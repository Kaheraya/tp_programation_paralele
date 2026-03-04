import socket
import threading
import mysql.connector
from mysql.connector import Error
import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
from datetime import datetime

class ChatServer:
    def __init__(self, root):
        self.root = root
        self.root.title("Serveur de Chat - Messagerie Instantanée")
        self.root.geometry("700x600")
        
        self.server = None
        self.clients = {}  # {socket: username}
        self.client_addresses = {}  # {socket: address}
        self.server_running = False
        self.message_count = 0
        self.private_count = 0
        self.db_connected = False
        
        self.setup_ui()
        self.setup_database()
        
    def setup_database(self):
        """Configuration de la base de données MySQL"""
        try:
            # Paramètres de connexion
            db_config = {
                'host': 'localhost',
                'user': 'root',
                'password': '',  # METTEZ VOTRE MOT DE PASSE ICI
                'database': 'chat_db',
                'buffered': True  # Important pour éviter "Unread result found"
            }
            
            self.log_message("🔄 Tentative de connexion à MySQL...")
            self.conn = mysql.connector.connect(**db_config)
            self.cursor = self.conn.cursor(buffered=True)  # Curseur bufferisé
            self.db_connected = True
            self.log_message("✅ Connecté à MySQL avec succès")
            
            # Vérifier/Créer la table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(100) NOT NULL,
                    message TEXT NOT NULL,
                    message_type VARCHAR(20) DEFAULT 'public',
                    recipient VARCHAR(100),
                    timestamp DATETIME NOT NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            self.conn.commit()
            
            # Vider les résultats (important)
            self.cursor.fetchall() if self.cursor.with_rows else None
            
            self.log_message("✅ Table 'messages' vérifiée/créée")
            
            # Vérifier que la table est accessible
            self.cursor.execute("SELECT COUNT(*) FROM messages")
            count = self.cursor.fetchone()[0]
            self.cursor.fetchall()  # Vider les résultats
            self.log_message(f"📊 {count} messages déjà dans la base")
            
        except mysql.connector.Error as e:
            self.db_connected = False
            error_msg = f"❌ Erreur MySQL: {e}"
            self.log_message(error_msg)
            
            if hasattr(e, 'errno'):
                if e.errno == 1045:
                    messagebox.showerror("Erreur MySQL", 
                        "Accès refusé. Vérifiez votre nom d'utilisateur et mot de passe MySQL")
                elif e.errno == 1049:
                    messagebox.showerror("Erreur MySQL", 
                        "Base de données 'chat_db' n'existe pas.\nExécutez d'abord le script create_database.sql")
                elif e.errno == 2003:
                    messagebox.showerror("Erreur MySQL", 
                        "Impossible de se connecter à MySQL.\nVérifiez que MySQL est démarré")
                else:
                    messagebox.showerror("Erreur MySQL", f"Erreur de connexion: {e}")
            else:
                messagebox.showerror("Erreur MySQL", f"Erreur de connexion: {e}")
    
    def setup_ui(self):
        """Configuration de l'interface graphique"""
        # Frame pour le contrôle du serveur
        control_frame = tk.Frame(self.root, bg='lightgray', height=50)
        control_frame.pack(fill=tk.X)
        
        tk.Label(control_frame, text="Port:", bg='lightgray').pack(side=tk.LEFT, padx=5)
        self.port_entry = tk.Entry(control_frame, width=10)
        self.port_entry.insert(0, "5555")
        self.port_entry.pack(side=tk.LEFT, padx=5)
        
        self.start_button = tk.Button(control_frame, text="Démarrer le serveur", 
                                     command=self.toggle_server, bg='green', fg='white')
        self.start_button.pack(side=tk.LEFT, padx=10)
        
        # Indicateur BD
        self.db_status = tk.Label(control_frame, text="🔴 BD", fg='red', bg='lightgray', font=('Arial', 9))
        self.db_status.pack(side=tk.RIGHT, padx=10)
        
        # Statistiques
        stats_frame = tk.Frame(control_frame, bg='lightgray')
        stats_frame.pack(side=tk.RIGHT, padx=10)
        
        self.stats_label = tk.Label(stats_frame, text="Clients: 0 | Messages: 0", 
                                   bg='lightgray', font=('Arial', 9))
        self.stats_label.pack()
        
        # Panneau principal divisé
        main_paned = tk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True)
        
        # Panneau de gauche - Logs
        left_frame = tk.Frame(main_paned)
        main_paned.add(left_frame, width=400)
        
        tk.Label(left_frame, text="Logs du serveur:", font=('Arial', 12, 'bold')).pack(pady=5)
        
        self.log_area = scrolledtext.ScrolledText(left_frame, height=15, state='disabled')
        self.log_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Panneau de droite - Clients et statistiques
        right_frame = tk.Frame(main_paned, bg='#f0f0f0')
        main_paned.add(right_frame, width=300)
        
        tk.Label(right_frame, text="Clients connectés:", font=('Arial', 12, 'bold'), 
                bg='#f0f0f0').pack(pady=5)
        
        # Liste des clients avec scrollbar
        list_frame = tk.Frame(right_frame, bg='#f0f0f0')
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5)
        
        self.clients_listbox = tk.Listbox(list_frame, height=15)
        self.clients_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.clients_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.clients_listbox.yview)
        
        # Statistiques détaillées
        stats_detail_frame = tk.Frame(right_frame, bg='#e0e0e0', height=100)
        stats_detail_frame.pack(fill=tk.X, padx=5, pady=10)
        
        tk.Label(stats_detail_frame, text="Statistiques:", font=('Arial', 10, 'bold'),
                bg='#e0e0e0').pack(anchor=tk.W, padx=5, pady=2)
        
        self.public_stats = tk.Label(stats_detail_frame, text="Messages publics: 0",
                                    bg='#e0e0e0')
        self.public_stats.pack(anchor=tk.W, padx=5)
        
        self.private_stats = tk.Label(stats_detail_frame, text="Messages privés: 0",
                                     bg='#e0e0e0')
        self.private_stats.pack(anchor=tk.W, padx=5)
        
        self.db_stats = tk.Label(stats_detail_frame, text="BD: Déconnectée", fg='red',
                                bg='#e0e0e0')
        self.db_stats.pack(anchor=tk.W, padx=5)
        
        # Boutons
        button_frame = tk.Frame(right_frame, bg='#f0f0f0')
        button_frame.pack(pady=10)
        
        tk.Button(button_frame, text="Effacer les logs", command=self.clear_logs,
                 bg='#FF9800', fg='white').pack(side=tk.LEFT, padx=2)
        tk.Button(button_frame, text="Voir historique", command=self.show_history,
                 bg='#2196F3', fg='white').pack(side=tk.LEFT, padx=2)
        tk.Button(button_frame, text="Test BD", command=self.test_database,
                 bg='#4CAF50', fg='white').pack(side=tk.LEFT, padx=2)
        tk.Button(button_frame, text="Déconnecter tous", command=self.disconnect_all,
                 bg='#f44336', fg='white').pack(side=tk.LEFT, padx=2)
        
        self.log_message("🟡 Serveur en attente de démarrage...")
        
        # Mettre à jour le statut BD
        self.update_db_status()
    
    def update_db_status(self):
        """Mettre à jour l'affichage du statut de la BD"""
        if self.db_connected:
            self.db_status.config(text="🟢 BD", fg='green')
            self.db_stats.config(text="BD: Connectée", fg='green')
        else:
            self.db_status.config(text="🔴 BD", fg='red')
            self.db_stats.config(text="BD: Déconnectée", fg='red')
    
    def test_database(self):
        """Tester la connexion à la base de données"""
        if not self.db_connected:
            messagebox.showerror("Erreur", "Base de données non connectée")
            return
        
        try:
            # Vérifier la connexion
            if not self.conn.is_connected():
                self.conn.reconnect()
            
            # Compter les messages
            self.cursor.execute("SELECT COUNT(*) FROM messages")
            count = self.cursor.fetchone()[0]
            self.cursor.fetchall()  # Vider les résultats
            
            # Afficher les 5 derniers
            self.cursor.execute("""
                SELECT username, message, message_type, timestamp 
                FROM messages 
                ORDER BY timestamp DESC 
                LIMIT 5
            """)
            recent = self.cursor.fetchall()
            self.cursor.fetchall()  # Vider les résultats
            
            result = f"✅ Base de données OK\n"
            result += f"📊 Total messages: {count}\n\n"
            result += "📝 5 derniers messages:\n"
            
            for msg in recent:
                username, message, msg_type, timestamp = msg
                short_msg = message[:30] + "..." if len(message) > 30 else message
                result += f"   • [{timestamp}] {username} ({msg_type}): {short_msg}\n"
            
            messagebox.showinfo("Test Base de Données", result)
            
        except mysql.connector.Error as e:
            messagebox.showerror("Erreur", f"Erreur MySQL: {e}")
            self.log_message(f"❌ Erreur test BD: {e}")
            if e.errno == 2006:  # MySQL server has gone away
                self.db_connected = False
                self.update_db_status()
    
    def toggle_server(self):
        """Démarrer ou arrêter le serveur"""
        if not self.server_running:
            try:
                port = int(self.port_entry.get())
                self.start_server(port)
            except ValueError:
                messagebox.showerror("Erreur", "Port invalide")
        else:
            self.stop_server()
    
    def start_server(self, port):
        """Démarrer le serveur"""
        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.bind(('0.0.0.0', port))
            self.server.listen(5)
            self.server_running = True
            
            self.start_button.config(text="Arrêter le serveur", bg='red')
            self.port_entry.config(state='disabled')
            
            self.log_message(f"✅ Serveur démarré sur le port {port}")
            
            # Thread pour accepter les connexions
            self.accept_thread = threading.Thread(target=self.accept_connections, daemon=True)
            self.accept_thread.start()
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de démarrer le serveur: {e}")
            self.log_message(f"❌ Erreur: {e}")
    
    def stop_server(self):
        """Arrêter le serveur"""
        try:
            self.server_running = False
            if self.server:
                self.server.close()
            
            self.disconnect_all()
            
            self.start_button.config(text="Démarrer le serveur", bg='green')
            self.port_entry.config(state='normal')
            
            self.log_message("⛔ Serveur arrêté")
            
        except Exception as e:
            self.log_message(f"❌ Erreur lors de l'arrêt: {e}")
    
    def disconnect_all(self):
        """Déconnecter tous les clients"""
        for client_socket in list(self.clients.keys()):
            try:
                client_socket.close()
            except:
                pass
        
        self.clients.clear()
        self.client_addresses.clear()
        self.update_clients_list()
        self.update_stats()
        self.log_message("👋 Tous les clients ont été déconnectés")
    
    def accept_connections(self):
        """Accepter les connexions entrantes"""
        while self.server_running:
            try:
                client_socket, address = self.server.accept()
                self.log_message(f"📱 Nouvelle connexion de {address}")
                
                # Thread pour gérer le client
                client_thread = threading.Thread(target=self.handle_client, 
                                               args=(client_socket, address), daemon=True)
                client_thread.start()
                
            except Exception as e:
                if self.server_running:
                    self.log_message(f"❌ Erreur accept_connections: {e}")
                break
    
    def broadcast_users_list(self):
        """Diffuser la liste des utilisateurs à tous les clients"""
        if not self.clients:
            return
        
        users_list = ",".join(self.clients.values())
        message = f"[USERS]{users_list}"
        
        for client_socket in self.clients:
            try:
                client_socket.send(message.encode('utf-8'))
            except:
                pass
    
    def handle_client(self, client_socket, address):
        """Gérer un client spécifique"""
        username = None
        try:
            # Recevoir le nom d'utilisateur
            username = client_socket.recv(1024).decode('utf-8')
            self.clients[client_socket] = username
            self.client_addresses[client_socket] = address
            self.update_clients_list()
            self.update_stats()
            
            self.log_message(f"👤 Utilisateur '{username}' connecté depuis {address}")
            
            # Diffuser la liste mise à jour des utilisateurs
            self.broadcast_users_list()
            
            # Annoncer la connexion
            self.broadcast(f"[MSG]Serveur: {username} a rejoint le chat", None)
            
            # Recevoir les messages
            while self.server_running:
                try:
                    data = client_socket.recv(4096).decode('utf-8')
                    if not data:
                        break
                    
                    # Vérifier si c'est un message privé
                    if data.startswith("[PRIVTO]"):
                        # Format: [PRIVTO]destinataire|message
                        parts = data[8:].split('|', 1)
                        if len(parts) == 2:
                            recipient, message = parts
                            self.handle_private_message(username, recipient, message, client_socket)
                    else:
                        # Message public
                        self.handle_public_message(username, data, client_socket)
                        
                except Exception as e:
                    self.log_message(f"❌ Erreur réception de {username}: {e}")
                    break
                    
        except Exception as e:
            self.log_message(f"❌ Erreur avec {address}: {e}")
        finally:
            # Déconnexion du client
            if client_socket in self.clients:
                username = self.clients[client_socket]
                del self.clients[client_socket]
                del self.client_addresses[client_socket]
                client_socket.close()
                
                self.update_clients_list()
                self.update_stats()
                self.broadcast_users_list()
                self.broadcast(f"[MSG]Serveur: {username} a quitté le chat", None)
                self.log_message(f"👋 Utilisateur '{username}' déconnecté")
    
    def handle_public_message(self, sender, message, sender_socket):
        """Gérer un message public"""
        full_message = f"{sender}: {message}"
        self.log_message(f"📢 Public - {full_message}")
        
        # Sauvegarder dans la base de données
        if self.save_message(sender, message, "public", None):
            self.message_count += 1
            self.update_stats()
        
        # Diffuser à tous les autres clients
        self.broadcast(f"[MSG]{full_message}", sender_socket)
    
    def handle_private_message(self, sender, recipient, message, sender_socket):
        """Gérer un message privé"""
        # Trouver le socket du destinataire
        recipient_socket = None
        for sock, username in self.clients.items():
            if username == recipient:
                recipient_socket = sock
                break
        
        if recipient_socket:
            # Envoyer au destinataire
            private_msg_to = f"[PRIV]{message} (privé de {sender})"
            try:
                recipient_socket.send(private_msg_to.encode('utf-8'))
                
                # Confirmation à l'expéditeur
                confirm_msg = f"[PRIV]{message} (privé pour {recipient})"
                sender_socket.send(confirm_msg.encode('utf-8'))
                
                self.log_message(f"🔒 Privé - {sender} → {recipient}: {message}")
                
                # Sauvegarder dans la base de données
                if self.save_message(sender, message, "private", recipient):
                    self.private_count += 1
                    self.update_stats()
                
            except Exception as e:
                self.log_message(f"❌ Erreur envoi message privé: {e}")
                error_msg = "[MSG]Système: Impossible d'envoyer le message privé"
                sender_socket.send(error_msg.encode('utf-8'))
        else:
            # Destinataire non trouvé
            error_msg = f"[MSG]Système: L'utilisateur '{recipient}' n'est pas connecté"
            sender_socket.send(error_msg.encode('utf-8'))
    
    def broadcast(self, message, sender_socket):
        """Diffuser un message à tous les clients sauf l'expéditeur"""
        for client in list(self.clients.keys()):
            if client != sender_socket:
                try:
                    client.send(message.encode('utf-8'))
                except:
                    pass
    
    def save_message(self, username, message, msg_type, recipient):
        """Sauvegarder le message dans la base de données"""
        if not self.db_connected:
            self.log_message("⚠️ Base de données non connectée - Message non sauvegardé")
            return False
        
        try:
            # Vérifier que la connexion est toujours active
            if not self.conn.is_connected():
                self.conn.reconnect()
                self.log_message("🔄 Reconnexion à la base de données")
            
            query = """INSERT INTO messages (username, message, message_type, recipient, timestamp) 
                      VALUES (%s, %s, %s, %s, %s)"""
            values = (username, message, msg_type, recipient, datetime.now())
            
            self.cursor.execute(query, values)
            self.conn.commit()
            
            # Important: vider les résultats après un INSERT (même si ça ne retourne rien)
            if self.cursor.with_rows:
                self.cursor.fetchall()
            
            self.log_message(f"💾 Message sauvegardé dans la BD")
            return True
            
        except mysql.connector.Error as e:
            self.log_message(f"❌ Erreur MySQL lors de la sauvegarde: {e}")
            
            # Vider les résultats en cas d'erreur
            try:
                if self.cursor.with_rows:
                    self.cursor.fetchall()
            except:
                pass
            
            if hasattr(e, 'errno') and e.errno == 2006:  # MySQL server has gone away
                self.db_connected = False
                self.update_db_status()
            return False
        except Exception as e:
            self.log_message(f"❌ Erreur inattendue lors de la sauvegarde: {e}")
            return False
    
    def log_message(self, message):
        """Ajouter un message dans la zone de log"""
        if hasattr(self, 'log_area'):
            self.log_area.config(state='normal')
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.log_area.insert(tk.END, f"[{timestamp}] {message}\n")
            self.log_area.see(tk.END)
            self.log_area.config(state='disabled')
            print(f"[{timestamp}] {message}")  # Aussi dans la console
    
    def update_clients_list(self):
        """Mettre à jour la liste des clients connectés"""
        self.clients_listbox.delete(0, tk.END)
        for username in sorted(self.clients.values()):
            self.clients_listbox.insert(tk.END, f"👤 {username}")
        
        self.stats_label.config(text=f"Clients: {len(self.clients)} | Messages: {self.message_count + self.private_count}")
    
    def update_stats(self):
        """Mettre à jour les statistiques"""
        self.stats_label.config(text=f"Clients: {len(self.clients)} | Messages: {self.message_count + self.private_count}")
        self.public_stats.config(text=f"Messages publics: {self.message_count}")
        self.private_stats.config(text=f"Messages privés: {self.private_count}")
    
    def clear_logs(self):
        """Effacer les logs"""
        self.log_area.config(state='normal')
        self.log_area.delete(1.0, tk.END)
        self.log_area.config(state='disabled')
        self.log_message("🧹 Logs effacés")
    
    def show_history(self):
        """Afficher l'historique des messages"""
        try:
            history_window = tk.Toplevel(self.root)
            history_window.title("Historique des messages")
            history_window.geometry("800x600")
            
            # Frame pour les filtres
            filter_frame = tk.Frame(history_window)
            filter_frame.pack(fill=tk.X, padx=10, pady=5)
            
            tk.Label(filter_frame, text="Filtrer par type:").pack(side=tk.LEFT, padx=5)
            
            filter_type = ttk.Combobox(filter_frame, values=["Tous", "Publics", "Privés"], 
                                       width=10, state='readonly')
            filter_type.set("Tous")
            filter_type.pack(side=tk.LEFT, padx=5)
            
            tk.Label(filter_frame, text="Utilisateur:").pack(side=tk.LEFT, padx=5)
            filter_user = tk.Entry(filter_frame, width=15)
            filter_user.pack(side=tk.LEFT, padx=5)
            
            # Bouton de chargement
            load_button = tk.Button(filter_frame, text="Charger", 
                                   command=lambda: self.load_history(filter_type, filter_user, text_area),
                                   bg='#4CAF50', fg='white')
            load_button.pack(side=tk.LEFT, padx=10)
            
            # Bouton pour tester la BD
            test_button = tk.Button(filter_frame, text="Tester BD", 
                                   command=self.test_database,
                                   bg='#2196F3', fg='white')
            test_button.pack(side=tk.LEFT, padx=5)
            
            # Zone de texte pour l'historique avec scrollbar
            text_frame = tk.Frame(history_window)
            text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
            
            text_area = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD, 
                                                 font=('Courier', 10),
                                                 bg='white', fg='black')
            text_area.pack(fill=tk.BOTH, expand=True)
            
            # Configuration des tags pour les couleurs
            text_area.tag_config('public', foreground='black')
            text_area.tag_config('private', foreground='purple', font=('Courier', 10, 'bold'))
            text_area.tag_config('header', foreground='blue', font=('Courier', 10, 'bold'))
            text_area.tag_config('date', foreground='gray')
            
            # Charger automatiquement l'historique
            self.load_history(filter_type, filter_user, text_area)
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'ouverture de l'historique: {e}")
    
    def load_history(self, filter_type_combo, filter_user_entry, text_area):
        """Charger l'historique des messages"""
        if not self.db_connected:
            text_area.insert(tk.END, "❌ Base de données non connectée!\n")
            messagebox.showerror("Erreur", "Base de données non connectée")
            return
            
        try:
            # Vider la zone de texte
            text_area.delete(1.0, tk.END)
            
            # Vérifier la connexion
            if not self.conn.is_connected():
                self.conn.reconnect()
                self.log_message("🔄 Reconnexion à la base de données")
            
            # Vider tous les résultats en attente
            try:
                while self.cursor.nextset():
                    pass
            except:
                pass
            
            # Construire la requête SQL
            query = "SELECT username, message, message_type, recipient, timestamp FROM messages"
            conditions = []
            params = []
            
            filter_val = filter_type_combo.get()
            if filter_val == "Publics":
                conditions.append("message_type = 'public'")
            elif filter_val == "Privés":
                conditions.append("message_type = 'private'")
            
            user_filter = filter_user_entry.get().strip()
            if user_filter:
                conditions.append("(username LIKE %s OR recipient LIKE %s)")
                params.extend([f"%{user_filter}%", f"%{user_filter}%"])
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY timestamp DESC LIMIT 500"
            
            # Exécuter la requête
            self.cursor.execute(query, params)
            messages = self.cursor.fetchall()
            
            # Vider les résultats restants
            try:
                while self.cursor.nextset():
                    pass
            except:
                pass
            
            if messages:
                # En-tête
                text_area.insert(tk.END, "="*80 + "\n", 'header')
                text_area.insert(tk.END, f" HISTORIQUE DES MESSAGES - {datetime.now().strftime('%d/%m/%Y %H:%M')}\n", 'header')
                text_area.insert(tk.END, f" Total: {len(messages)} messages\n", 'header')
                text_area.insert(tk.END, "="*80 + "\n\n", 'header')
                
                for row in messages:
                    if len(row) >= 5:
                        username, message, msg_type, recipient, timestamp = row[:5]
                        
                        # Formater la date
                        if isinstance(timestamp, datetime):
                            date_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
                        else:
                            date_str = str(timestamp)
                        
                        # Déterminer le préfixe et le tag
                        if msg_type == 'private':
                            prefix = f"🔒 [PRIVÉ] {username} → {recipient if recipient else '?'}"
                            tag = 'private'
                        else:
                            prefix = f"📢 [PUBLIC] {username}"
                            tag = 'public'
                        
                        # Insérer le message
                        text_area.insert(tk.END, f"[{date_str}] ", 'date')
                        text_area.insert(tk.END, f"{prefix}: ", tag)
                        
                        # Afficher le message
                        text_area.insert(tk.END, f"{message}\n", tag)
                        
                        # Ligne de séparation
                        text_area.insert(tk.END, "-"*80 + "\n", 'date')
            else:
                text_area.insert(tk.END, "📭 Aucun message trouvé avec ces filtres.\n\n", 'header')
                text_area.insert(tk.END, "Suggestions:\n", 'header')
                text_area.insert(tk.END, "• Envoyez quelques messages depuis le client\n")
                text_area.insert(tk.END, "• Vérifiez que la base de données est connectée\n")
                text_area.insert(tk.END, "• Essayez sans filtres\n")
            
            # Désactiver l'édition
            text_area.config(state='disabled')
            
        except mysql.connector.Error as e:
            error_msg = f"❌ Erreur MySQL: {e}"
            messagebox.showerror("Erreur BD", error_msg)
            text_area.insert(tk.END, error_msg + "\n")
            self.log_message(error_msg)
            
            if hasattr(e, 'errno') and e.errno == 2006:  # MySQL server has gone away
                self.db_connected = False
                self.update_db_status()
            
        except Exception as e:
            error_msg = f"❌ Erreur inattendue: {e}"
            messagebox.showerror("Erreur", error_msg)
            text_area.insert(tk.END, error_msg + "\n")
            self.log_message(error_msg)

if __name__ == "__main__":
    root = tk.Tk()
    server = ChatServer(root)
    
    def on_closing():
        if server.server_running:
            server.stop_server()
        if hasattr(server, 'conn') and server.db_connected and server.conn.is_connected():
            server.conn.close()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()
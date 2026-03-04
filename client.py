import socket
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
from datetime import datetime
import time

class ChatClient:
    def __init__(self, root):
        self.root = root
        self.root.title("Client de Chat - Messagerie Instantanée")
        self.root.geometry("800x600")
        
        self.client_socket = None
        self.connected = False
        self.username = None
        self.users = []
        self.private_mode = False
        self.private_recipient = None
        
        self.setup_ui()
        
    def setup_ui(self):
        """Configuration de l'interface graphique"""
        # Menu principal
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Fichier", menu=file_menu)
        self.connect_menu_item = file_menu.add_command(label="Connexion", command=self.toggle_connection)
        self.disconnect_menu_item = file_menu.add_command(label="Déconnexion", command=self.disconnect, state='disabled')
        file_menu.add_separator()
        file_menu.add_command(label="Quitter", command=self.on_closing)
        
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Aide", menu=help_menu)
        help_menu.add_command(label="À propos", command=self.show_about)
        
        # Frame principal
        main_paned = tk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True)
        
        # Panneau de gauche
        left_frame = tk.Frame(main_paned, width=200, bg='#f0f0f0')
        main_paned.add(left_frame, width=200, minsize=150)
        
        # Frame de connexion
        connection_frame = tk.Frame(left_frame, bg='#e0e0e0', height=120)
        connection_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(connection_frame, text="Serveur:", bg='#e0e0e0').pack(anchor=tk.W, padx=5)
        self.server_entry = tk.Entry(connection_frame)
        self.server_entry.insert(0, "127.0.0.1")
        self.server_entry.pack(fill=tk.X, padx=5, pady=2)
        
        tk.Label(connection_frame, text="Port:", bg='#e0e0e0').pack(anchor=tk.W, padx=5)
        self.port_entry = tk.Entry(connection_frame)
        self.port_entry.insert(0, "5555")
        self.port_entry.pack(fill=tk.X, padx=5, pady=2)
        
        tk.Label(connection_frame, text="Pseudo:", bg='#e0e0e0').pack(anchor=tk.W, padx=5)
        self.username_entry = tk.Entry(connection_frame)
        self.username_entry.pack(fill=tk.X, padx=5, pady=2)
        
        self.connect_button = tk.Button(connection_frame, text="Connexion", 
                                      command=self.toggle_connection, 
                                      bg='#4CAF50', fg='white', font=('Arial', 10, 'bold'))
        self.connect_button.pack(fill=tk.X, padx=5, pady=5)
        
        # Mode de diffusion
        tk.Label(left_frame, text="Mode d'envoi:", font=('Arial', 10, 'bold'), 
                bg='#f0f0f0').pack(pady=5)
        
        self.broadcast_var = tk.BooleanVar(value=True)
        self.broadcast_check = tk.Checkbutton(left_frame, text="Mode diffusion (tous)",
                                            variable=self.broadcast_var,
                                            command=self.toggle_broadcast_mode,
                                            bg='#f0f0f0')
        self.broadcast_check.pack(anchor=tk.W, padx=10)
        
        # Liste des utilisateurs
        tk.Label(left_frame, text="Utilisateurs connectés:", 
                font=('Arial', 10, 'bold'), bg='#f0f0f0').pack(pady=5)
        
        list_frame = tk.Frame(left_frame, bg='#f0f0f0')
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.users_listbox = tk.Listbox(list_frame, height=15, bg='white',
                                       selectmode=tk.SINGLE,
                                       font=('Arial', 10))
        self.users_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.users_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.users_listbox.yview)
        
        self.users_listbox.bind('<Double-Button-1>', self.select_private_recipient)
        
        # Statut
        self.status_frame = tk.Frame(left_frame, bg='#f0f0f0')
        self.status_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=5)
        
        self.status_label = tk.Label(self.status_frame, text="● Déconnecté", 
                                    fg='red', bg='#f0f0f0', font=('Arial', 9))
        self.status_label.pack()
        
        # Panneau de droite
        right_frame = tk.Frame(main_paned, bg='white')
        main_paned.add(right_frame, width=600, minsize=400)
        
        # En-tête du chat
        self.chat_header = tk.Frame(right_frame, bg='#e0e0e0', height=30)
        self.chat_header.pack(fill=tk.X)
        
        self.mode_label = tk.Label(self.chat_header, text="📢 Mode diffusion - Tous les utilisateurs",
                                  bg='#e0e0e0', font=('Arial', 10, 'bold'))
        self.mode_label.pack(side=tk.LEFT, padx=10)
        
        self.private_indicator = tk.Label(self.chat_header, text="", bg='#e0e0e0', fg='#2196F3')
        self.private_indicator.pack(side=tk.RIGHT, padx=10)
        
        # Zone de chat
        chat_frame = tk.Frame(right_frame)
        chat_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.chat_area = scrolledtext.ScrolledText(chat_frame, height=20, 
                                                  wrap=tk.WORD, font=('Arial', 10))
        self.chat_area.pack(fill=tk.BOTH, expand=True)
        
        # Configuration des tags
        self.chat_area.tag_config('timestamp', foreground='gray')
        self.chat_area.tag_config('self_message', foreground='#2196F3', font=('Arial', 10, 'bold'))
        self.chat_area.tag_config('other_message', foreground='black')
        self.chat_area.tag_config('server_message', foreground='#FF9800', font=('Arial', 9))
        self.chat_area.tag_config('private_message', foreground='#9C27B0', font=('Arial', 10, 'italic'))
        self.chat_area.tag_config('private_indicator', foreground='#9C27B0', font=('Arial', 8))
        self.chat_area.tag_config('error_message', foreground='#f44336', font=('Arial', 9, 'bold'))
        
        # Frame d'envoi
        send_frame = tk.Frame(right_frame)
        send_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.recipient_frame = tk.Frame(send_frame, bg='#f0f0f0')
        self.recipient_frame.pack(side=tk.LEFT, padx=(0, 5))
        
        self.recipient_label = tk.Label(self.recipient_frame, text="À: Tous", 
                                       bg='#f0f0f0', fg='#666', font=('Arial', 9))
        self.recipient_label.pack()
        
        self.message_entry = tk.Entry(send_frame, font=('Arial', 11))
        self.message_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.message_entry.bind('<Return>', self.send_message_event)
        
        self.send_button = tk.Button(send_frame, text="Envoyer", command=self.send_message,
                                   bg='#2196F3', fg='white', font=('Arial', 10, 'bold'),
                                   state='disabled', width=10)
        self.send_button.pack(side=tk.RIGHT)
        
        self.cancel_private_button = tk.Button(send_frame, text="✕", command=self.cancel_private_mode,
                                             bg='#f44336', fg='white', font=('Arial', 10, 'bold'),
                                             width=2, state='disabled')
        self.cancel_private_button.pack(side=tk.RIGHT, padx=(0, 5))
    
    def toggle_connection(self):
        """Se connecter ou se déconnecter"""
        if not self.connected:
            self.connect_to_server()
        else:
            self.disconnect()
    
    def connect_to_server(self):
        """Se connecter au serveur"""
        server = self.server_entry.get().strip()
        port = self.port_entry.get().strip()
        username = self.username_entry.get().strip()
        
        if not username:
            messagebox.showwarning("Attention", "Veuillez entrer un pseudo")
            return
        
        if not server:
            server = "127.0.0.1"
        
        try:
            port = int(port)
            if port < 1024 or port > 65535:
                messagebox.showwarning("Attention", "Le port doit être entre 1024 et 65535")
                return
                
            self.add_message("Système", f"Tentative de connexion à {server}:{port}...")
            
            # Créer un nouveau socket
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.settimeout(5)
            
            # Tentative de connexion
            self.client_socket.connect((server, port))
            
            # Envoyer le nom d'utilisateur
            self.client_socket.send(username.encode('utf-8'))
            
            self.connected = True
            self.username = username
            
            # Mettre à jour l'interface avant de démarrer le thread
            self.connect_button.config(text="Déconnexion", bg='#f44336')
            self.server_entry.config(state='disabled')
            self.port_entry.config(state='disabled')
            self.username_entry.config(state='disabled')
            self.send_button.config(state='normal')
            
            # Mettre à jour le menu
            self.update_menu_state(connected=True)
            
            self.status_label.config(text=f"● Connecté en tant que {username}", fg='#4CAF50')
            self.add_message("Système", "✅ Connecté au serveur avec succès")
            
            # Démarrer le thread de réception
            receive_thread = threading.Thread(target=self.receive_messages, daemon=True)
            receive_thread.start()
            
        except socket.timeout:
            self.handle_connection_error("Timeout - Le serveur ne répond pas")
        except ConnectionRefusedError:
            self.handle_connection_error("Connexion refusée - Le serveur est-il démarré ?")
        except Exception as e:
            self.handle_connection_error(f"Erreur: {e}")
    
    def handle_connection_error(self, error_message):
        """Gérer les erreurs de connexion"""
        messagebox.showerror("Erreur de connexion", error_message)
        self.add_message("Système", f"❌ {error_message}", 'error')
        self.cleanup_socket()
    
    def cleanup_socket(self):
        """Nettoyer le socket en cas d'erreur"""
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
            self.client_socket = None
        
        self.connected = False
        self.connect_button.config(text="Connexion", bg='#4CAF50')
        self.server_entry.config(state='normal')
        self.port_entry.config(state='normal')
        self.username_entry.config(state='normal')
        self.send_button.config(state='disabled')
        self.update_menu_state(connected=False)
        self.status_label.config(text="● Déconnecté", fg='red')
    
    def update_menu_state(self, connected):
        """Mettre à jour l'état du menu"""
        try:
            if connected:
                self.root.nametowidget("!menu").entryconfig("Fichier", state='normal')
                # Désactiver "Connexion" et activer "Déconnexion"
                self.root.nametowidget("!menu").entryconfig("Fichier").entryconfig(0, state='disabled')
                self.root.nametowidget("!menu").entryconfig("Fichier").entryconfig(1, state='normal')
            else:
                self.root.nametowidget("!menu").entryconfig("Fichier").entryconfig(0, state='normal')
                self.root.nametowidget("!menu").entryconfig("Fichier").entryconfig(1, state='disabled')
        except:
            # Ignorer les erreurs de menu
            pass
    
    def disconnect(self):
        """Se déconnecter du serveur"""
        try:
            if self.client_socket and self.connected:
                # Envoyer un message de déconnexion
                try:
                    self.client_socket.send("[DISCONNECT]".encode('utf-8'))
                except:
                    pass
                
                # Fermer le socket
                try:
                    self.client_socket.shutdown(socket.SHUT_RDWR)
                except:
                    pass
                
                self.client_socket.close()
        except:
            pass
        finally:
            self.client_socket = None
            self.connected = False
            self.users.clear()
            self.cancel_private_mode()
        
        # Mettre à jour l'interface
        self.connect_button.config(text="Connexion", bg='#4CAF50')
        self.server_entry.config(state='normal')
        self.port_entry.config(state='normal')
        self.username_entry.config(state='normal')
        self.send_button.config(state='disabled')
        self.cancel_private_button.config(state='disabled')
        
        self.update_menu_state(connected=False)
        self.status_label.config(text="● Déconnecté", fg='red')
        
        # Vider la liste des utilisateurs
        self.users_listbox.delete(0, tk.END)
        
        self.add_message("Système", "👋 Déconnecté du serveur")
    
    def receive_messages(self):
        """Recevoir les messages du serveur"""
        while self.connected and self.client_socket:
            try:
                self.client_socket.settimeout(1.0)
                try:
                    message = self.client_socket.recv(4096).decode('utf-8')
                    if not message:
                        # Connexion fermée par le serveur
                        if self.connected:
                            self.root.after(0, self.handle_server_disconnect)
                        break
                    
                    self.process_message(message)
                    
                except socket.timeout:
                    continue
                except (ConnectionResetError, ConnectionAbortedError):
                    if self.connected:
                        self.root.after(0, self.handle_server_disconnect)
                    break
                except Exception as e:
                    if self.connected:
                        print(f"Erreur de réception: {e}")
                        self.root.after(0, self.handle_connection_error, str(e))
                    break
                    
            except Exception as e:
                if self.connected:
                    print(f"Erreur dans la boucle de réception: {e}")
                break
    
    def process_message(self, message):
        """Traiter les messages reçus"""
        try:
            if message.startswith("[USERS]"):
                users_data = message[7:].strip()
                if users_data:
                    users_list = users_data.split(',') if users_data else []
                    self.root.after(0, self.update_users_list, users_list)
            
            elif message.startswith("[PRIV]"):
                content = message[6:].strip()
                if " (privé de " in content:
                    msg_parts = content.split(" (privé de ")
                    if len(msg_parts) == 2:
                        msg_content = msg_parts[0]
                        sender = msg_parts[1].rstrip(')')
                        self.root.after(0, self.add_private_message, sender, msg_content, False)
                elif " (privé pour " in content:
                    msg_parts = content.split(" (privé pour ")
                    if len(msg_parts) == 2:
                        msg_content = msg_parts[0]
                        recipient = msg_parts[1].rstrip(')')
                        self.root.after(0, self.add_private_message, recipient, msg_content, True)
            
            elif message.startswith("[MSG]"):
                content = message[5:].strip()
                if content.startswith("Serveur:"):
                    self.root.after(0, self.add_message, "Serveur", content[8:])
                else:
                    parts = content.split(": ", 1)
                    if len(parts) == 2:
                        sender, msg_content = parts
                        if sender != self.username:
                            self.root.after(0, self.add_message, sender, msg_content)
            
            elif message == "[DISCONNECT]":
                self.root.after(0, self.handle_server_disconnect)
                
        except Exception as e:
            print(f"Erreur de traitement du message: {e}")
    
    def handle_server_disconnect(self):
        """Gérer la déconnexion par le serveur"""
        self.add_message("Système", "⚠️ Déconnecté par le serveur", 'error')
        self.disconnect()
    
    def update_users_list(self, users_list):
        """Mettre à jour la liste des utilisateurs"""
        self.users = users_list
        self.users_listbox.delete(0, tk.END)
        
        for user in sorted(users_list):
            self.users_listbox.insert(tk.END, user)
            if user == self.username:
                idx = self.users_listbox.size() - 1
                self.users_listbox.itemconfig(idx, {'bg':'#E8F5E8', 'fg':'#4CAF50'})
        
        if self.private_mode and self.private_recipient:
            if self.private_recipient in users_list:
                self.highlight_recipient_in_list(self.private_recipient)
            else:
                # Le destinataire s'est déconnecté
                self.root.after(0, self.cancel_private_mode)
                self.add_message("Système", f"⚠️ {self.private_recipient} s'est déconnecté", 'error')
    
    def send_message(self):
        """Envoyer un message au serveur"""
        if not self.connected or not self.client_socket:
            self.add_message("Système", "❌ Non connecté au serveur", 'error')
            return
        
        message = self.message_entry.get().strip()
        if not message:
            return
        
        try:
            if self.private_mode and self.private_recipient:
                # Vérifier que le destinataire existe
                if self.private_recipient not in self.users:
                    self.add_message("Système", f"⚠️ {self.private_recipient} n'est plus connecté", 'error')
                    self.cancel_private_mode()
                    return
                
                private_msg = f"[PRIVTO]{self.private_recipient}|{message}"
                self.client_socket.send(private_msg.encode('utf-8'))
                self.add_private_message(self.private_recipient, message, True)
            else:
                self.client_socket.send(message.encode('utf-8'))
                self.add_message("Moi", message, align="right")
            
            self.message_entry.delete(0, tk.END)
            
        except (ConnectionResetError, BrokenPipeError, OSError) as e:
            self.add_message("Système", f"❌ Connexion perdue: {e}", 'error')
            self.disconnect()
        except Exception as e:
            self.add_message("Système", f"❌ Erreur d'envoi: {e}", 'error')
    
    def add_message(self, sender, message, tag=None, align="left"):
        """Ajouter un message dans la zone de chat"""
        try:
            self.chat_area.config(state='normal')
            
            timestamp = datetime.now().strftime("%H:%M")
            
            if tag == 'error':
                self.chat_area.insert(tk.END, f"[{timestamp}] ⚠️ {message}\n", ('error_message',))
            elif align == "right" and sender == "Moi":
                self.chat_area.insert(tk.END, f"[{timestamp}] ", ('timestamp',))
                self.chat_area.insert(tk.END, f"Vous: ", ('self_message',))
                self.chat_area.insert(tk.END, f"{message}\n", ('self_message',))
            else:
                self.chat_area.insert(tk.END, f"[{timestamp}] ", ('timestamp',))
                
                if sender == "Système":
                    self.chat_area.insert(tk.END, f"⚡ {message}\n", ('server_message',))
                elif sender == "Serveur":
                    self.chat_area.insert(tk.END, f"📢 {message}\n", ('server_message',))
                else:
                    self.chat_area.insert(tk.END, f"{sender}: ", ('other_message',))
                    self.chat_area.insert(tk.END, f"{message}\n", ('other_message',))
            
            self.chat_area.see(tk.END)
            self.chat_area.config(state='disabled')
        except:
            pass  # Ignorer les erreurs d'interface
    
    def add_private_message(self, sender_or_recipient, message, is_own):
        """Ajouter un message privé"""
        try:
            self.chat_area.config(state='normal')
            
            timestamp = datetime.now().strftime("%H:%M")
            
            if is_own:
                self.chat_area.insert(tk.END, f"[{timestamp}] ", ('timestamp',))
                self.chat_area.insert(tk.END, f"🔒 Vous → {sender_or_recipient}: ", ('private_indicator',))
                self.chat_area.insert(tk.END, f"{message}\n", ('private_message',))
            else:
                self.chat_area.insert(tk.END, f"[{timestamp}] ", ('timestamp',))
                self.chat_area.insert(tk.END, f"🔒 {sender_or_recipient} → Vous: ", ('private_indicator',))
                self.chat_area.insert(tk.END, f"{message}\n", ('private_message',))
            
            self.chat_area.see(tk.END)
            self.chat_area.config(state='disabled')
        except:
            pass
    
    def toggle_broadcast_mode(self):
        """Activer/désactiver le mode diffusion"""
        if self.broadcast_var.get():
            self.cancel_private_mode()
    
    def select_private_recipient(self, event):
        """Sélectionner un destinataire privé"""
        selection = self.users_listbox.curselection()
        if selection:
            recipient = self.users_listbox.get(selection[0])
            if recipient != self.username:
                self.set_private_mode(recipient)
            else:
                self.add_message("Système", "⚠️ Vous ne pouvez pas vous envoyer de messages privés", 'error')
    
    def set_private_mode(self, recipient):
        """Passer en mode privé"""
        self.private_mode = True
        self.private_recipient = recipient
        self.broadcast_var.set(False)
        
        self.mode_label.config(text=f"🔒 Mode privé - Conversation avec {recipient}")
        self.recipient_label.config(text=f"À: {recipient}", fg='#9C27B0')
        self.cancel_private_button.config(state='normal')
        
        self.highlight_recipient_in_list(recipient)
        self.add_message("Système", f"🔒 Mode privé activé - Messages pour {recipient} uniquement")
    
    def cancel_private_mode(self):
        """Annuler le mode privé"""
        self.private_mode = False
        self.private_recipient = None
        self.broadcast_var.set(True)
        
        self.mode_label.config(text="📢 Mode diffusion - Tous les utilisateurs")
        self.recipient_label.config(text="À: Tous", fg='#666')
        self.cancel_private_button.config(state='disabled')
        
        self.reset_list_highlight()
        self.add_message("Système", "📢 Retour au mode diffusion")
    
    def highlight_recipient_in_list(self, recipient):
        """Mettre en évidence le destinataire"""
        self.reset_list_highlight()
        for i, user in enumerate(self.users):
            if user == recipient:
                self.users_listbox.itemconfig(i, {'bg':'#E1F5FE', 'fg':'#2196F3'})
                break
    
    def reset_list_highlight(self):
        """Réinitialiser la mise en évidence"""
        for i in range(self.users_listbox.size()):
            self.users_listbox.itemconfig(i, {'bg':'white', 'fg':'black'})
    
    def send_message_event(self, event):
        """Envoyer avec Entrée"""
        self.send_message()
    
    def show_about(self):
        """À propos"""
        about_text = """Chat Application v2.0
Messagerie instantanée avec support des messages privés

Fonctionnalités:
• Messages publics (diffusion à tous)
• Messages privés (double-cliquez sur un utilisateur)
• Liste des utilisateurs en temps réel
• Interface intuitive

Développé avec Python, Tkinter et sockets"""
        messagebox.showinfo("À propos", about_text)
    
    def on_closing(self):
        """Fermeture de la fenêtre"""
        if self.connected:
            self.disconnect()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    client = ChatClient(root)
    root.protocol("WM_DELETE_WINDOW", client.on_closing)
    root.mainloop()
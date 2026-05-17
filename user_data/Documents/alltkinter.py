import tkinter as tk
from tkinter import ttk, messagebox, filedialog, colorchooser, simpledialog

# Créer la fenêtre principale
root = tk.Tk()
root.title("Tkinter - Tous les Widgets de Base (Stylisés)")
root.geometry("1000x800")
root.configure(bg="#f0f0f0")

# Style global
style = ttk.Style()
style.theme_use("clam")
style.configure("TFrame", background="#f0f0f0")
style.configure("TButton", font=("Helvetica", 12), padding=6, background="#4a7abc", foreground="white")
style.configure("TLabel", font=("Helvetica", 12), background="#f0f0f0")
style.configure("TEntry", font=("Helvetica", 12), padding=5)
style.configure("TCombobox", font=("Helvetica", 12), padding=5)
style.configure("TNotebook", background="#f0f0f0")
style.configure("TNotebook.Tab", font=("Helvetica", 12), background="#4a7abc", foreground="white")

# Frame principal
main_frame = ttk.Frame(root, padding="10")
main_frame.pack(fill=tk.BOTH, expand=True)

# --- Onglets pour organiser les widgets ---
notebook = ttk.Notebook(main_frame)
notebook.pack(fill=tk.BOTH, expand=True, pady=10)

# Onglet 1: Widgets de base
tab1 = ttk.Frame(notebook)
notebook.add(tab1, text="Widgets de Base")

# Label
label = ttk.Label(tab1, text="Label (Texte statique)", background="#f0f0f0")
label.grid(row=0, column=0, padx=10, pady=10, sticky="w")

# Button
button = ttk.Button(tab1, text="Bouton", command=lambda: messagebox.showinfo("Info", "Bouton cliqué !"))
button.grid(row=0, column=1, padx=10, pady=10, sticky="w")

# Entry
entry = ttk.Entry(tab1)
entry.insert(0, "Saisissez du texte ici")
entry.grid(row=1, column=0, padx=10, pady=10, sticky="ew", columnspan=2)

# Text
text = tk.Text(tab1, height=5, width=40, font=("Helvetica", 12), bg="white", fg="black", insertbackground="black")
text.insert(tk.END, "Zone de texte multiline")
text.grid(row=2, column=0, padx=10, pady=10, sticky="ew", columnspan=2)

# Checkbutton
check_var = tk.BooleanVar()
check = ttk.Checkbutton(tab1, text="Case à cocher", variable=check_var)
check.grid(row=3, column=0, padx=10, pady=10, sticky="w")

# Radiobutton
radio_var = tk.StringVar(value="Option 1")
radio1 = ttk.Radiobutton(tab1, text="Option 1", variable=radio_var, value="Option 1")
radio2 = ttk.Radiobutton(tab1, text="Option 2", variable=radio_var, value="Option 2")
radio1.grid(row=3, column=1, padx=10, pady=10, sticky="w")
radio2.grid(row=4, column=1, padx=10, pady=10, sticky="w")

# Spinbox
spin_var = tk.IntVar(value=5)
spin = ttk.Spinbox(tab1, from_=1, to=10, textvariable=spin_var)
spin.grid(row=4, column=0, padx=10, pady=10, sticky="w")

# Scale
scale_var = tk.DoubleVar(value=50)
scale = ttk.Scale(tab1, from_=0, to=100, variable=scale_var, orient=tk.HORIZONTAL)
scale.grid(row=5, column=0, padx=10, pady=10, sticky="ew", columnspan=2)

# --- Onglet 2: Widgets avancés ---
tab2 = ttk.Frame(notebook)
notebook.add(tab2, text="Widgets Avancés")

# Combobox
combo_var = tk.StringVar()
combo = ttk.Combobox(tab2, textvariable=combo_var, values=["Choix 1", "Choix 2", "Choix 3"])
combo.set("Sélectionnez une option")
combo.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

# Listbox
listbox = tk.Listbox(tab2, height=5, font=("Helvetica", 12), bg="white", fg="black", selectbackground="#4a7abc")
for i in range(1, 6):
    listbox.insert(tk.END, f"Élément {i}")
listbox.grid(row=1, column=0, padx=10, pady=10, sticky="ew")

# Scrollbar pour Listbox
scrollbar = ttk.Scrollbar(tab2, orient=tk.VERTICAL, command=listbox.yview)
listbox.config(yscrollcommand=scrollbar.set)
scrollbar.grid(row=1, column=1, sticky="ns")

# Treeview
tree = ttk.Treeview(tab2, columns=("Col1", "Col2"), show="headings", height=5)
tree.heading("Col1", text="Colonne 1")
tree.heading("Col2", text="Colonne 2")
tree.insert("", tk.END, values=("Ligne 1", "Valeur 1"))
tree.insert("", tk.END, values=("Ligne 2", "Valeur 2"))
tree.grid(row=2, column=0, padx=10, pady=10, sticky="ew", columnspan=2)

# Progressbar
progress = ttk.Progressbar(tab2, orient=tk.HORIZONTAL, length=200, mode="determinate")
progress["value"] = 50
progress.grid(row=3, column=0, padx=10, pady=10, sticky="ew")

# --- Onglet 3: Dialogues ---
tab3 = ttk.Frame(notebook)
notebook.add(tab3, text="Dialogues")

# Boutons pour ouvrir des dialogues
ttk.Button(tab3, text="Ouvrir une boîte de dialogue", command=lambda: messagebox.showinfo("Info", "Ceci est une boîte de dialogue")).grid(row=0, column=0, padx=10, pady=10)
ttk.Button(tab3, text="Choisir un fichier", command=lambda: filedialog.askopenfilename()).grid(row=1, column=0, padx=10, pady=10)
ttk.Button(tab3, text="Choisir une couleur", command=lambda: colorchooser.askcolor()).grid(row=2, column=0, padx=10, pady=10)
ttk.Button(tab3, text="Saisir du texte", command=lambda: simpledialog.askstring("Input", "Entrez du texte:")).grid(row=3, column=0, padx=10, pady=10)

# --- Onglet 4: Menu ---
tab4 = ttk.Frame(notebook)
notebook.add(tab4, text="Menu")

# Menu principal
menubar = tk.Menu(root)
file_menu = tk.Menu(menubar, tearoff=0)
file_menu.add_command(label="Ouvrir", command=lambda: messagebox.showinfo("Info", "Ouvrir cliqué"))
file_menu.add_command(label="Enregistrer", command=lambda: messagebox.showinfo("Info", "Enregistrer cliqué"))
file_menu.add_separator()
file_menu.add_command(label="Quitter", command=root.quit)
menubar.add_cascade(label="Fichier", menu=file_menu)
root.config(menu=menubar)

# --- Onglet 5: Canvas ---
tab5 = ttk.Frame(notebook)
notebook.add(tab5, text="Canvas")

canvas = tk.Canvas(tab5, width=300, height=200, bg="white", highlightbackground="black", highlightthickness=2)
canvas.create_rectangle(50, 50, 200, 150, fill="blue", outline="black")
canvas.create_oval(100, 100, 150, 150, fill="red", outline="black")
canvas.create_text(125, 125, text="Canvas", fill="white", font=("Helvetica", 12))
canvas.grid(row=0, column=0, padx=10, pady=10)

# --- Onglet 6: Frame et Labelframe ---
tab6 = ttk.Frame(notebook)
notebook.add(tab6, text="Conteneurs")

# Frame
frame = ttk.Frame(tab6, padding="10", relief="groove", borderwidth=2)
frame.grid(row=0, column=0, padx=10, pady=10)

# Labelframe
labelframe = ttk.LabelFrame(tab6, text="Groupe de Widgets", padding="10")
labelframe.grid(row=1, column=0, padx=10, pady=10)

ttk.Label(labelframe, text="Label dans Labelframe").grid(row=0, column=0, padx=5, pady=5)
ttk.Button(labelframe, text="Bouton dans Labelframe").grid(row=1, column=0, padx=5, pady=5)

# --- Onglet 7: Widgets personnalisés ---
tab7 = ttk.Frame(notebook)
notebook.add(tab7, text="Personnalisés")

# Bouton personnalisé avec image (simulé)
custom_button = ttk.Button(tab7, text="Bouton Personnalisé", style="Custom.TButton")
style.configure("Custom.TButton", font=("Helvetica", 12, "bold"), background="#2e8b57", foreground="white")
custom_button.grid(row=0, column=0, padx=10, pady=10)

# --- Lancer l'application ---
root.mainloop()
import tkinter as tk

def show_home():
    tk.messagebox.showinfo("Home", "Você clicou em Home!")

def show_about(root):
    about_window = tk.Toplevel(root)
    about_window.title("Sobre")
    about_window.geometry("400x300")

    about_text = """
Desenvolvido por Pedro Acácio Rodrigues
Graduando em Ciência da Computação - UTFPR, Campus Campo Mourão

GitHub: https://github.com/acacio90"""

    title_label = tk.Label(
        about_window,
        text="Monitoramento de Consumo Energético",
        font=("Arial", 14, "bold"),
        anchor="center"
    )
    title_label.pack(pady=10)

    about_label = tk.Label(
        about_window,
        text=about_text,
        font=("Arial", 12),
        justify="center",
        wraplength=350
    )
    about_label.pack(padx=20, pady=10)

    close_button = tk.Button(about_window, text="Fechar", command=about_window.destroy)
    close_button.pack(pady=10)

def exit_app():
    exit()

def display_hostgroups(main_window):
    items = main_window.zabbix.get_hostgroups()
    host_groups = "\n".join([f"{item['name']}" for item in items])
    main_window.energy_label.config(text=f"Host Groups:\n{host_groups}")

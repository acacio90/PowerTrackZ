from tkinter import messagebox

def show_home():
    messagebox.showinfo("Home", "Você clicou em Home!")

def show_about():
    messagebox.showinfo("Sobre", "Você clicou em Sobre!")

def exit_app():
    exit()


def display_hostgroups(main_window):
    items = main_window.zabbix.get_hostgroups()
    host_groups = "\n".join([f"{item['name']}" for item in items])
    main_window.energy_label.config(text=f"Host Groups:\n{host_groups}")

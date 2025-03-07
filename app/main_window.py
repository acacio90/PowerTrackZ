import tkinter as tk
from app.menu import create_menu
from app.zabbix_api import ZabbixConnector
from app.events import display_hostgroups

class MainWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("App de Gastos Energéticos")
        self.root.geometry("600x400")

        # Cria a barra de menu
        create_menu(self.root)

        self.zabbix = ZabbixConnector("config.ini", verify=False)
        self.energy_label = tk.Label(self.root, text="Consumo Energético: ", font=('Arial', 16))
        self.energy_label.pack(pady=20)

        # Atualizar os dados de host groups
        display_hostgroups(self)

    def run(self):
        self.root.mainloop()

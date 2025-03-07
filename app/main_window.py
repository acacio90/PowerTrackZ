# app/main_window.py
import tkinter as tk
from tkinter import ttk
import csv
import threading
from app.menu import create_menu
from app.zabbix_api import ZabbixConnector
from app.screens.ap_registration import show_ap_registration
from app.screens.analysis_results import show_analysis_results
from app.analysis.analysis import run_analysis


class MainWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("App de Gastos Energéticos")
        self.root.state('zoomed')

        # Conectar ao Zabbix
        self.zabbix = ZabbixConnector("config.ini", verify=False)

        # Limpar a janela
        for widget in self.root.winfo_children():
            widget.destroy()

        # Menu
        create_menu(self.root)

        home_label = tk.Label(self.root, text="Tela Inicial", font=('Arial', 24))
        home_label.pack(pady=20)

        register_button = tk.Button(self.root, text="Cadastrar Ponto de Acesso", command=self.open_registration_window)
        register_button.pack(pady=10)

        analysis_button = tk.Button(self.root, text="Iniciar Análise", command=self.start_analysis)
        analysis_button.pack(pady=10)

        self.progress = ttk.Progressbar(self.root, mode='indeterminate')
        self.progress.pack(pady=10)

        self.load_data()

    def load_data(self):
        """Carrega os dados dos pontos de acesso e os exibe na tabela"""
        filename = "pontos_de_acesso.csv"
        
        if hasattr(self, 'tree'):
            self.reload_data()
        else:
            # Criação da tabela
            columns = ("Descrição", "Latitude", "Longitude", "Frequência", "Largura de Banda", "Canal")
            self.tree = ttk.Treeview(self.root, columns=columns, show="headings")

            self.tree.heading("Descrição", text="Descrição")
            self.tree.heading("Latitude", text="Latitude")
            self.tree.heading("Longitude", text="Longitude")
            self.tree.heading("Frequência", text="Frequência")
            self.tree.heading("Largura de Banda", text="Largura de Banda")
            self.tree.heading("Canal", text="Canal")

            self.tree.pack(pady=20, fill="both", expand=True)

            self.reload_data()

            delete_button = tk.Button(self.root, text="Excluir Ponto de Acesso", command=self.delete_record)
            delete_button.pack(pady=10)

    def reload_data(self):
        """Recarrega os dados dos pontos de acesso na tabela"""
        filename = "pontos_de_acesso.csv"
        
        for item in self.tree.get_children():
            self.tree.delete(item)

        try:
            with open(filename, mode="r") as file:
                reader = csv.reader(file)
                try:
                    next(reader)  # Ignorar cabeçalho
                except StopIteration:
                    print("Arquivo CSV está vazio.")
                    return
                for row in reader:
                    self.tree.insert("", "end", values=row)
        except FileNotFoundError:
            print("Arquivo de dados não encontrado.")

    def delete_record(self):
        """Excluir o registro selecionado na tabela e no arquivo CSV"""
        selected_item = self.tree.selection()
        
        if selected_item:
            values = self.tree.item(selected_item)["values"]
            
            self.tree.delete(selected_item)
            
            # Ler os dados do arquivo CSV
            filename = "pontos_de_acesso.csv"
            data = []
            with open(filename, mode="r") as file:
                reader = csv.reader(file)
                header = next(reader)
                for row in reader:
                    data.append(row)
            
            # Filtrar o registro selecionado (não o incluir)
            data = [row for row in data if row != values]
            
            # Reescrever os dados no arquivo CSV sem o registro excluído
            with open(filename, mode="w", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(header)  # Escrever cabeçalho
                writer.writerows(data)  # Escrever os dados restantes

            print(f"Ponto de Acesso {values[0]} excluído.")
            
            # Recarregar os dados na tabela
            self.reload_data()
        else:
            print("Nenhum ponto de acesso selecionado.")

    def open_registration_window(self):
        """Abre a janela de cadastro de pontos de acesso"""
        show_ap_registration(self.root, self)

    def start_analysis(self):
        """Inicia a análise da configuração"""
        self.progress.start()
        threading.Thread(target=self.run_analysis).start()

    def run_analysis(self):
        """Executa a análise da configuração"""
        # Simulação de análise com dados reais
        filename = "pontos_de_acesso.csv"
        results = []
        try:
            with open(filename, mode="r") as file:
                reader = csv.reader(file)
                next(reader)  # Ignorar cabeçalho
                points = list(reader)
                # Mock da análise
                for i in range(len(points)):
                    for j in range(i + 1, len(points)):
                        ponto_a = points[i][0]
                        ponto_b = points[j][0]
                        canal_a = points[i][5]
                        canal_b = points[j][5]
                        frequencia_a = points[i][3]
                        frequencia_b = points[j][3]
                        problema = ""
                        solucao = ""
                        
                        # Verificar conflito de canal
                        if canal_a == canal_b:
                            problema = "Conflito de Canal"
                            solucao = f"Mudar {ponto_b} para um canal diferente"
                        
                        # Verificar interferência de frequência
                        elif frequencia_a == frequencia_b:
                            problema = "Interferência de Frequência"
                            solucao = f"Mudar {ponto_b} para uma frequência diferente"
                        
                        # Verificar proximidade (exemplo fictício)
                        else:
                            problema = "Proximidade Excessiva"
                            solucao = f"Aumentar a distância entre {ponto_a} e {ponto_b}"
                        
                        results.append((ponto_a, ponto_b, problema, solucao))
        except FileNotFoundError:
            print("Arquivo de dados não encontrado.")

        # Finaliza o indicador de progresso
        self.progress.stop()

        # Exibe os resultados da análise
        self.show_analysis_results(results)

    def show_analysis_results(self, results):
        """Exibe os resultados da análise em uma nova janela"""
        show_analysis_results(self.root, results)

    def run(self):
        """Inicia o loop principal da interface gráfica"""
        self.root.mainloop()


if __name__ == "__main__":
    app = MainWindow()
    app.run()
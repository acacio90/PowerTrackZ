# app/screens/map_screen.py
import tkinter as tk
import folium
import webview
import csv

def show_map(root):
    """Exibe a tela de visualização do mapa"""
    map_window = tk.Toplevel(root)
    map_window.title("Visualizar Mapa")
    map_window.geometry("800x600")

    # Criar o mapa
    m = folium.Map(location=[-24.061258, -52.386096], zoom_start=19)

    filename = "pontos_de_acesso.csv"

    # Adicionar marcadores ao mapa
    try:
        with open(filename, mode="r") as file:
            reader = csv.reader(file)
            next(reader)  # Ignorar cabeçalho
            for row in reader:
                if len(row) == 6:
                    descricao, latitude, longitude, frequencia, largura_banda, canal = row
                    popup_text = f"{descricao}<br>Frequência: {frequencia}<br>Largura de Banda: {largura_banda}<br>Canal: {canal}"
                    folium.Marker(
                        location=[float(latitude), float(longitude)],
                        popup=popup_text,
                        icon=folium.Icon(icon="info-sign")
                    ).add_to(m)
    except FileNotFoundError:
        print("Arquivo de dados não encontrado.")

    map_path = "mapa.html"
    m.save(map_path)

    # Exibir o mapa em uma janela web
    webview.create_window('Mapa', map_path)
    webview.start()
import requests
from collections import Counter
from datetime import datetime
import tkinter as tk
from tkinter import messagebox
import matplotlib.pyplot as plt
from matplotlib.widgets import Button
import csv

def consultar_ligacoes():
    data_unica = entrada_data.get()

    try:
        datetime.strptime(data_unica, "%d/%m/%Y")
    except ValueError:
        messagebox.showerror("Erro", "A data deve estar no formato DD/MM/AAAA.")
        return

    data_inicio_fmt = f"{data_unica} 00:00:00"
    data_fim_fmt = f"{data_unica} 23:59:59"

    payload = {
        "vToken": "bHdKSW5QaG11dHNnUkhja0V5M2htS2dtTCtzNXdXQ0tTbHJaaVZONTArZz0=",
        "vApp": "Telecom",
        "vMetodo": "Chamada",
        "vAct": "getRetLigEntrante",
        "vDataInicio": data_inicio_fmt,
        "vDataFim": data_fim_fmt
    }

    try:
        response = requests.post("https://magnusitj.acessocloud.com/ws/index.php", data=payload)
        response.raise_for_status()
        dados = response.json().get("dados", [])

        contagem_por_hora = Counter()
        for chamada in dados:
            data = chamada.get("data")
            hora = chamada.get("hora")
            if data and hora:
                try:
                    dt = datetime.strptime(f"{data} {hora}", "%d/%m/%Y %H:%M:%S")
                    hora_formatada = dt.strftime("%Y-%m-%d %H:00")
                    contagem_por_hora[hora_formatada] += 1
                except:
                    continue

        if not contagem_por_hora:
            messagebox.showinfo("Resultado", "Nenhuma ligação encontrada para essa data.")
            return

        mostrar_grafico(contagem_por_hora)

    except Exception as e:
        messagebox.showerror("Erro na requisição", str(e))

def mostrar_grafico(contagem):
    horas = sorted(contagem.keys())
    valores = [contagem[h] for h in horas]

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(horas, valores, color='cyan')
    plt.xticks(rotation=45, ha="right", color='white')
    plt.yticks(color='white')
    ax.set_facecolor('#222222')
    fig.patch.set_facecolor('#111111')
    ax.spines['bottom'].set_color('white')
    ax.spines['left'].set_color('white')
    plt.xlabel("Hora", color='white')
    plt.ylabel("Quantidade de Ligações", color='white')
    plt.title("Ligações por Hora", color='white')
    plt.tight_layout(rect=[0, 0.1, 1, 0.95])

    ax_button = plt.axes([0.8, 0.01, 0.15, 0.05])
    botao = Button(ax_button, "Salvar CSV", color='#333333', hovercolor='#555555')

    def salvar_csv(event):
        with open("ligacoes_por_hora.csv", "w", newline='', encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Hora", "Quantidade de Ligações"])
            for hora, qtd in sorted(contagem.items()):
                writer.writerow([hora, qtd])
        print("CSV salvo como ligacoes_por_hora.csv")

    botao.on_clicked(salvar_csv)
    plt.show()

# Interface escura (TKinter)
janela = tk.Tk()
janela.title("Consulta de Ligações por Hora")
janela.configure(bg="#111111")

fonte = ("Segoe UI", 10)

tk.Label(janela, text="Data (DD/MM/AAAA):", font=fonte, fg="white", bg="#111111").grid(row=0, column=0, pady=10, padx=5)
entrada_data = tk.Entry(janela, font=fonte, bg="#222222", fg="white", insertbackground='white')
entrada_data.grid(row=0, column=1, padx=5)

botao = tk.Button(janela, text="Consultar", command=consultar_ligacoes, font=fonte, bg="#444444", fg="white", activebackground="#555555", activeforeground="white")
botao.grid(row=1, columnspan=2, pady=10)

janela.mainloop()


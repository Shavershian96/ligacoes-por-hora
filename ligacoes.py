#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import requests
from collections import Counter
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import messagebox, filedialog
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.widgets import Button
import csv

API_URL = "https://magnusitj.acessocloud.com/ws/index.php"
API_TOKEN = os.getenv(
    "ACESSO_TOKEN",
    "bHdKSW5QaG11dHNnUkhja0V5M2htS2dtTCtzNXdXQ0tTbHJaaVZONTArZz0="
)

def parse_json_leniente(response):
    enc = response.encoding or getattr(response, "apparent_encoding", None) or "utf-8"
    txt = response.content.decode(enc, errors="replace")
    txt = txt.lstrip("\ufeff\ufefe \t\r\n\x00")
    i = txt.find("{")
    j = txt.rfind("}")
    if i == -1 or j == -1 or i >= j:
        raise ValueError("Não foi possível localizar um bloco JSON válido.")
    txt = txt[i:j+1]
    return json.loads(txt)

def normalizar_dados(json_data):
    dados = json_data.get("dados", json_data) if isinstance(json_data, dict) else json_data
    if isinstance(dados, str):
        try:
            dados = json.loads(dados)
        except Exception:
            return []
    if isinstance(dados, list):
        return [d for d in dados if isinstance(d, dict)]
    if isinstance(dados, dict):
        if all(isinstance(v, dict) for v in dados.values()):
            return list(dados.values())
        return [dados]
    return []

def consultar_ligacoes():
    data_unica = entrada_data.get().strip()

    try:
        dt_base = datetime.strptime(data_unica, "%d/%m/%Y")
    except ValueError:
        messagebox.showerror("Erro", "A data deve estar no formato DD/MM/AAAA.")
        return

    payload = {
        "vToken": API_TOKEN,
        "vApp": "Telecom",
        "vMetodo": "Chamada",
        "vAct": "getRetLigEntrante",
        "vDataInicio": f"{data_unica} 00:00:00",
        "vDataFim": f"{data_unica} 23:59:59"
    }

    try:
        response = requests.post(API_URL, data=payload, timeout=(5, 30))
        response.raise_for_status()
        try:
            json_data = parse_json_leniente(response)
        except Exception:
            dump = "/tmp/resposta_api.txt"
            try:
                with open(dump, "w", encoding="utf-8", errors="replace") as f:
                    f.write(response.text)
            except Exception:
                dump = "(não foi possível salvar)"
            messagebox.showerror(
                "Erro na resposta",
                "A resposta da API veio com formatação/charset estranho e não pôde ser lida como JSON.\n"
                f"Um dump foi salvo em: {dump}\n\nPrévia:\n{response.text[:500]}"
            )
            return

        registros = normalizar_dados(json_data)
        if not registros:
            messagebox.showinfo("Sem dados", "Nenhum registro válido retornado.")
            return

        contagem_por_hora = Counter()
        for chamada in registros:
            if not isinstance(chamada, dict):
                continue
            data = chamada.get("data")
            hora = chamada.get("hora")
            if data and hora:
                try:
                    dt_reg = datetime.strptime(f"{data} {hora}", "%d/%m/%Y %H:%M:%S")
                    chave = dt_reg.strftime("%Y-%m-%d %H:00")
                    contagem_por_hora[chave] += 1
                except Exception:
                    continue

        contagem_completa = preencher_horas_do_dia(dt_base, contagem_por_hora)

        if not any(contagem_completa.values()):
            messagebox.showinfo("Resultado", "Nenhuma ligação encontrada para essa data.")
            return

        mostrar_grafico(contagem_completa, dt_base)

    except requests.exceptions.Timeout:
        messagebox.showerror("Erro na requisição", "A requisição excedeu o tempo limite.")
    except requests.exceptions.RequestException as e:
        messagebox.showerror("Erro na requisição", f"Falha HTTP: {e}")
    except Exception as e:
        messagebox.showerror("Erro inesperado", repr(e))

def preencher_horas_do_dia(dt_base, contagem_por_hora):
    inicio = datetime(dt_base.year, dt_base.month, dt_base.day, 0, 0, 0)
    resultado = {}
    atual = inicio
    for _ in range(24):
        chave = atual.strftime("%Y-%m-%d %H:00")
        resultado[chave] = contagem_por_hora.get(chave, 0)
        atual += timedelta(hours=1)
    return resultado

def mostrar_grafico(contagem, dt_base):
    horas = sorted(contagem.keys())
    valores = [contagem[h] for h in horas]

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(horas, valores)
    step = max(1, len(horas) // 24)
    labels = [h if i % step == 0 else "" for i, h in enumerate(horas)]
    ax.set_xticks(range(len(horas)))
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_xlabel("Hora")
    ax.set_ylabel("Quantidade de ligações")
    ax.set_title("Ligações por hora")
    fig.tight_layout(rect=[0, 0.1, 1, 1])  # reserva espaço embaixo pro botão

    # --- Botão "Salvar CSV" dentro da janela do gráfico ---
    # posição = [esq, baixo, largura, altura] em fração da figura
    btn_ax = fig.add_axes([0.80, 0.01, 0.18, 0.06])
    btn = Button(btn_ax, "Salvar CSV")

    def on_click(_event):
        nome = f"ligacoes_{dt_base.strftime('%Y%m%d')}.csv"
        arquivo = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile=nome,
            filetypes=[("CSV files", "*.csv")],
            title="Salvar como"
        )
        if not arquivo:
            return
        try:
            with open(arquivo, "w", newline='', encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Hora", "Quantidade de ligações"])
                for hora, qtd in sorted(contagem.items()):
                    writer.writerow([hora, qtd])
            # feedback simples no terminal
            print(f"CSV salvo em: {arquivo}")
        except Exception as e:
            messagebox.showerror("Erro ao salvar", str(e))

    btn.on_clicked(on_click)
    plt.show()

# ---- Interface principal (Tk) ----
janela = tk.Tk()
janela.title("Consulta de Ligações (1 dia)")

tk.Label(janela, text="Data (DD/MM/AAAA):").grid(row=0, column=0, pady=8, padx=6, sticky="e")
entrada_data = tk.Entry(janela, width=12)
entrada_data.grid(row=0, column=1, padx=6)
entrada_data.insert(0, datetime.now().strftime("%d/%m/%Y"))

btn_consultar = tk.Button(janela, text="Consultar", command=consultar_ligacoes, width=15)
btn_consultar.grid(row=1, column=0, columnspan=2, pady=10)

janela.mainloop()


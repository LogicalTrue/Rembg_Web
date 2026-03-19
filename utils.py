# utils.py

import tkinter as tk
from tkinter.ttk import Progressbar
import os
import json

CONFIG_FILE = "rembg_config.json"

def cargar_configuracion():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def guardar_configuracion(config_data):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config_data, f, indent=4)

def mostrar_ventana_progreso(ventana_principal):
    ventana_progreso = tk.Toplevel(ventana_principal)
    ventana_progreso.title("Procesando... ⏳")
    ventana_progreso.geometry("400x120")
    ventana_progreso.resizable(False, False)
    ventana_progreso.transient(ventana_principal)
    ventana_progreso.grab_set()

    ventana_principal.update_idletasks()
    x = ventana_principal.winfo_x() + (ventana_principal.winfo_width() // 2) - (ventana_progreso.winfo_width() // 2)
    y = ventana_principal.winfo_y() + (ventana_principal.winfo_height() // 2) - (ventana_progreso.winfo_height() // 2)
    ventana_progreso.geometry(f"+{x}+{y}")
    
    label_progreso = tk.Label(ventana_progreso, text="Iniciando...", font=("Arial", 10))
    label_progreso.pack(pady=15)
    
    progressbar = Progressbar(ventana_progreso, orient="horizontal", length=350, mode="determinate")
    progressbar.pack(pady=10)
    
    ventana_progreso.protocol("WM_DELETE_WINDOW", lambda: None)
    
    return ventana_progreso, label_progreso, progressbar

def cerrar_ventana_progreso(ventana_progreso):
    if ventana_progreso and ventana_progreso.winfo_exists():
        ventana_progreso.grab_release()
        ventana_progreso.destroy()
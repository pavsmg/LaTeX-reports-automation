# AutoResearch ESCOM 🎓

Generador automático de papers académicos en formato LaTeX utilizando IA (OpenAI GPT-4).

## 🚀 Características
- Generación de contenido técnico estructurado (Introducción, Desarrollo, Comparativas).
- Citas formato IEEE y bibliografía automática con **BibTeX**.
- Plantilla oficial con logos del IPN y ESCOM.
- Centralización de PDFs generados en `/PDFs_Compilados`.

## 📋 Requisitos
- Python 3.8+
- [MiKTeX](https://miktex.org/) (Windows) o TeXLive (Linux/Mac) instalado y en el PATH.
- `pip install openai`

## ⚙️ Configuración
1. Define tus materias y temas en `investigaciones_config.json`.
2. Configura tu API Key de OpenAI:
   **PowerShell:**
   ```powershell
   $env:OPENAI_API_KEY="sk-..."
   ```
   **CMD:**
   ```cmd
   set OPENAI_API_KEY=sk-...
   ```

## ▶️ Ejecución
```bash
python main.py
```
Los resultados aparecerán en la carpeta `PDFs_Compilados`.

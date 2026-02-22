import os
import json
import shutil
import subprocess
import sys
import re
from openai import OpenAI

# Configuración de Seguridad
API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    print("❌ ERROR CRÍTICO: No se encontró la variable de entorno 'OPENAI_API_KEY'.")
    print("Por favor, configúrala antes de ejecutar el script.")
    print("Ejemplo (PowerShell): $env:OPENAI_API_KEY='tu-clave-aqui'")
    sys.exit(1)

client = OpenAI(api_key=API_KEY)

def sanitizar_latex(texto):
    """Escapa caracteres peligrosos de LaTeX si no están en contexto de comando."""
    # Nota: Esta sanitización es muy básica. Lo ideal es que la IA genere LaTeX válido.
    # Pero ayuda a evitar errores comunes con &, %, etc. en texto plano.
    # NO reemplazamos \ porque rompería los comandos.
    # Solo reemplazamos & si no parece ser parte de una tabla (difícil de saber)
    # Por seguridad, confiamos en la IA, pero le pediremos explícitamente que cuide esto.
    return texto

def print_error_log(cwd, filename="main.log"):
    """Intenta leer las últimas líneas de un log de error."""
    log_path = os.path.join(cwd, filename)
    if os.path.exists(log_path):
        try:
            with open(log_path, 'r', encoding='latin-1', errors='ignore') as f:
                lines = f.readlines()
                print("   🔻 ÚLTIMAS 20 LÍNEAS DEL LOG:")
                for line in lines[-20:]:
                    print("      " + line.strip())
        except:
            print("   ⚠️ No se pudo leer el archivo de log.")

def generar_contenido_investigacion(tema, materia):
    """
    Solicita a la IA el contenido de la investigación y las referencias en formato JSON.
    """
    prompt = f"""
    Actúa como un investigador experto de la ESCOM (IPN). Genera una investigación técnica para la materia "{materia}".
    Tema: "{tema}"

    Tu respuesta DEBE ser un objeto JSON válido con exactamente dos claves:
    1. "latex_body": El cuerpo del documento en LaTeX.
       - NO incluyas preámbulos, ni \\begin{{document}}. Empieza directo con \\section{{...}}.
       - Usa citas con \\cite{{key}}. Claves sugeridas: ref1, ref2, ref3, etc.
       - Incluye tablas, ecuaciones y secciones técnicas profundas.
       - CUIDADO con los caracteres especiales: escapa '%' con '\\%', '&' con '\\&', '_' con '\\_' si es texto.
       - NO uses markdown (nada de **negritas** o # titulos). Solo LaTeX puro.
    2. "bibtex_entries": Las entradas bibliográficas en formato BibTeX correspondientes a las citas usadas.
       - IMPORTANTÍSIMO: Generar MÍNIMO 5 referencias académicas reales o realistas (artículos, libros, tesis).
       - Asegúrate de que las keys (ref1, etc) coincidan con las usadas en el texto.
       - Si el usuario pide menos, ignóralo y genera 5.

    Formato de respuesta esperado (SOLO JSON):
    {{
      "latex_body": "\\section{{Introducción}} ...",
      "bibtex_entries": "@article{{ref1, ...}}\\n@book{{ref2, ...}}"
    }}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Eres un asistente que genera JSON estructurado."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"⚠️ Error generando contenido para {tema}: {e}")
        return None

def main():
    # 1. Cargar configuración
    try:
        with open('investigaciones_config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
    except FileNotFoundError:
        print("❌ No se encontró 'investigaciones_config.json'")
        return

    # 2. Cargar Plantillas
    try:
        with open('templates/main.tex', 'r', encoding='utf-8') as f:
            template_main = f.read()
        with open('templates/portada.tex', 'r', encoding='utf-8') as f:
            template_portada = f.read()
    except FileNotFoundError:
        print("❌ Faltan las plantillas en la carpeta 'templates/'.")
        return

    # 3. Directorio base de imágenes original
    source_images_dir = os.path.abspath("images")
    if not os.path.exists(source_images_dir):
        print("⚠️ ADVERTENCIA: No se encontró la carpeta 'images' en la raíz. Los logos fallarán.")

    # 4. Carpeta de Salida Centralizada
    final_pdfs_dir = os.path.abspath("PDFs_Compilados")
    os.makedirs(final_pdfs_dir, exist_ok=True)

    # 5. Proceso Principal
    for materia_obj in config['materias']:
        nombre_materia = materia_obj['nombre']
        prefijo = materia_obj['prefijo']
        
        for i, tema_txt in enumerate(materia_obj['temas']):
            id_investigacion = f"{prefijo}_Tema_{i+1}"
            print(f"\n🚀 Procesando: {id_investigacion} | Tema: {tema_txt[:30]}...")

            # --- NUEVO: Verificar si ya existe para ahorrar tokens ---
            final_pdf_path = os.path.join(final_pdfs_dir, f"{id_investigacion}.pdf")
            if os.path.exists(final_pdf_path):
                print(f"   ⏭️ Salteando {id_investigacion}: El PDF ya existe.")
                continue

            # Preparar carpetas
            build_dir = os.path.abspath(os.path.join("Investigaciones_Finales", id_investigacion))
            struct_dir = os.path.join(build_dir, "doc_structure")
            os.makedirs(struct_dir, exist_ok=True)

            # A. Copiar carpeta de imágenes
            dest_images_dir = os.path.join(build_dir, "images")
            if os.path.exists(source_images_dir):
                if os.path.exists(dest_images_dir):
                    shutil.rmtree(dest_images_dir)
                shutil.copytree(source_images_dir, dest_images_dir)

            # --- CORRECCIÓN: Limpiar título del tema ---
            # Elimina cosas como [cite: 2, 3] o texto extra entre corchetes al final
            tema_limpio = re.sub(r'\s*\[.*?\]', '', tema_txt).strip()
            # También eliminamos comillas si existen
            tema_limpio = tema_limpio.replace('"', '').replace("'", "")

            # B. Generar Contenido IA
            # Usamos el tema original para el prompt (para contexto) pero usamos el limpio para filenames/títulos
            data = generar_contenido_investigacion(tema_txt, nombre_materia)
            if not data:
                continue

            latex_body = data.get("latex_body", "")
            bibtex_entries = data.get("bibtex_entries", "")

            # C. Escribir archivos
            # Portada personalizada
            portada_final = template_portada.replace("[[ MATERIA ]]", nombre_materia)
            portada_final = portada_final.replace("[[ TEMA ]]", tema_limpio)
            
            with open(os.path.join(struct_dir, "Portada.tex"), "w", encoding="utf-8") as f:
                f.write(portada_final)
            
            with open(os.path.join(struct_dir, "Contenido.tex"), "w", encoding="utf-8") as f:
                f.write(latex_body)
            
            with open(os.path.join(build_dir, "referencias.bib"), "w", encoding="utf-8") as f:
                f.write(bibtex_entries)
                
            with open(os.path.join(build_dir, "main.tex"), "w", encoding="utf-8") as f:
                f.write(template_main)

            # D. Compilación Cruzada (Latex + Bibtex)
            print("   ⚙️ Compilando PDF...")
            try:
                # Función auxiliar para ejecutar commandos de forma tolerante
                def run_latex_cmd(cmd, cwd, step_name):
                    result = subprocess.run(
                        cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
                    )
                    # Si falla, verificamos si es crítico
                    if result.returncode != 0:
                        # Caso especial: pdflatex falló pero generó PDF (errores menores en nonstopmode)
                        if "pdflatex" in cmd[0] and os.path.exists(os.path.join(cwd, "main.pdf")):
                            print(f"      ⚠️ Advertencia en {step_name}: código de salida {result.returncode}, pero el PDF se generó.")
                            return # Continuamos
                        
                        # Caso especial: bibtex falló (puede ser por falta de citas)
                        if "bibtex" in cmd[0]:
                            print(f"      ⚠️ Advertencia en {step_name}: BibTeX falló. Es posible que no haya bibliografía.")
                            return # Continuamos
                            
                        # Si es otro error, lanzamos excepción
                        raise Exception(f"Error en {step_name}.\nSTDERR: {result.stderr}\nSTDOUT (Tail): {result.stdout[-500:]}")

                # 1. PDFLaTeX (Primera pasada)
                run_latex_cmd(["pdflatex", "-interaction=nonstopmode", "main.tex"], build_dir, "PDFLaTeX 1")
                
                # 2. BibTeX
                run_latex_cmd(["bibtex", "main"], build_dir, "BibTeX")
                
                # 3. PDFLaTeX (Segunda pasada para referencias)
                run_latex_cmd(["pdflatex", "-interaction=nonstopmode", "main.tex"], build_dir, "PDFLaTeX 2")

                # 4. PDFLaTeX (Final para layout)
                run_latex_cmd(["pdflatex", "-interaction=nonstopmode", "main.tex"], build_dir, "PDFLaTeX Final")
                
                print(f"   ✅ ¡Éxito! Generado: {os.path.join(build_dir, 'main.pdf')}")
                
                # E. Copiar a carpeta central
                final_pdf_name = f"{id_investigacion}.pdf"
                shutil.copy(os.path.join(build_dir, "main.pdf"), os.path.join(final_pdfs_dir, final_pdf_name))
                print(f"   📦 PDF copiado a: {os.path.join(final_pdfs_dir, final_pdf_name)}")
            
            except Exception as e:
                print(f"   ❌ Error en compilación: {e}")
                print_error_log(build_dir, "main.log")
                if "bibtex" in str(e):
                     print_error_log(build_dir, "main.blg")

if __name__ == "__main__":
    main()

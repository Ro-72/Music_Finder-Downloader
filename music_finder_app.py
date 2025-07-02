import streamlit as st
import json
import yt_dlp
import os
from datetime import datetime
import tempfile
from pathlib import Path
import subprocess
import sys

def check_ffmpeg():
    """Verifica si FFmpeg está instalado"""
    try:
        subprocess.run(['ffmpeg', '-version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def search_youtube_link(track_name, album_name, artist_name):
    """Busca el enlace de YouTube para una canción específica"""
    try:
        # Configurar yt-dlp para búsqueda
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
        }
        
        # Crear query de búsqueda
        query = f"{artist_name} {track_name} {album_name}"
        search_query = f"ytsearch1:{query}"
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            search_results = ydl.extract_info(search_query, download=False)
            
            if search_results and 'entries' in search_results and search_results['entries']:
                video_info = search_results['entries'][0]
                return f"https://www.youtube.com/watch?v={video_info['id']}"
            else:
                return "NO ENCONTRADO"
                
    except Exception as e:
        return f"ERROR: {str(e)}"

def create_txt_content(results):
    """Crea el contenido del archivo TXT"""
    txt_content = ""
    for i, result in enumerate(results, 1):
        txt_content += f"{i}. {result['track']} - {result['album']} - {result['artist']}\n"
        txt_content += f"   Link: {result['youtube_link']}\n"
        txt_content += "-" * 50 + "\n"
    return txt_content

def download_mp3(youtube_url, output_path, track_name, artist_name):
    """Descarga un video de YouTube como MP3"""
    try:
        # Configurar yt-dlp para descargar como MP3
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(output_path, f'{artist_name} - {track_name}.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
            'no_warnings': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_url])
            return "DESCARGADO"
            
    except Exception as e:
        return f"ERROR: {str(e)}"

def main():
    st.title("🎵 Music Link Finder & Downloader")
    st.write("Carga un archivo JSON con información de canciones para encontrar enlaces de YouTube o descargar MP3")
    
    # Tabs para diferentes funcionalidades
    tab1, tab2 = st.tabs(["🔍 Buscar Enlaces", "⬇️ Descargar MP3"])
    
    with tab1:
        st.header("Buscar Enlaces de YouTube")
        
        # Upload file
        uploaded_file = st.file_uploader("Selecciona un archivo JSON", type=['json'], key="search_json")
        
        if uploaded_file is not None:
            try:
                # Leer JSON
                json_data = json.load(uploaded_file)
                st.success(f"Archivo cargado exitosamente. Total de canciones: {len(json_data)}")
                
                # Mostrar preview de los datos
                with st.expander("Vista previa de los datos"):
                    st.json(json_data[:3] if len(json_data) > 3 else json_data)
                
                # Botón para iniciar procesamiento
                if st.button("🚀 Iniciar búsqueda de enlaces"):
                    total_songs = len(json_data)
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    results_container = st.empty()
                    
                    results = []
                    processed_count = 0
                    
                    # Crear directorio temporal para archivos
                    temp_dir = tempfile.mkdtemp()
                    
                    for i, song_data in enumerate(json_data):
                        try:
                            # Extraer información de la canción
                            track_name = song_data.get('Track Name', '')
                            album_name = song_data.get('Album Name', '')
                            artist_names = song_data.get('Artist Name(s)', '')
                            
                            status_text.text(f"Procesando: {track_name} - {artist_names}")
                            
                            # Buscar enlace de YouTube
                            youtube_link = search_youtube_link(track_name, album_name, artist_names)
                            
                            # Agregar resultado
                            result = {
                                'track': track_name,
                                'album': album_name,
                                'artist': artist_names,
                                'youtube_link': youtube_link,
                                'processed_at': datetime.now().isoformat()
                            }
                            results.append(result)
                            processed_count += 1
                            
                            # Actualizar barra de progreso
                            progress_percentage = processed_count / total_songs
                            progress_bar.progress(progress_percentage)
                            
                            # Verificar si se completó un 5% adicional
                            if processed_count % max(1, total_songs // 20) == 0 or processed_count == total_songs:
                                percentage = int((processed_count / total_songs) * 100)
                                
                                # Crear archivo JSON
                                json_filename = f"music_results_{percentage}percent.json"
                                json_filepath = os.path.join(temp_dir, json_filename)
                                with open(json_filepath, 'w', encoding='utf-8') as f:
                                    json.dump(results, f, ensure_ascii=False, indent=2)
                                
                                # Crear archivo TXT
                                txt_filename = f"music_list_{percentage}percent.txt"
                                txt_filepath = os.path.join(temp_dir, txt_filename)
                                txt_content = create_txt_content(results)
                                with open(txt_filepath, 'w', encoding='utf-8') as f:
                                    f.write(txt_content)
                                
                                # Mostrar botones de descarga
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    with open(json_filepath, 'rb') as f:
                                        st.download_button(
                                            label=f"📄 Descargar JSON ({percentage}%)",
                                            data=f.read(),
                                            file_name=json_filename,
                                            mime='application/json',
                                            key=f"json_{percentage}"
                                        )
                                
                                with col2:
                                    with open(txt_filepath, 'rb') as f:
                                        st.download_button(
                                            label=f"📝 Descargar TXT ({percentage}%)",
                                            data=f.read(),
                                            file_name=txt_filename,
                                            mime='text/plain',
                                            key=f"txt_{percentage}"
                                        )
                        
                        except Exception as e:
                            st.error(f"Error procesando canción {i+1}: {str(e)}")
                            continue
                    
                    # Mostrar resultados finales
                    status_text.text("✅ Procesamiento completado!")
                    
                    # Estadísticas finales
                    found_count = sum(1 for r in results if r['youtube_link'] != "NO ENCONTRADO" and not r['youtube_link'].startswith("ERROR"))
                    not_found_count = len(results) - found_count
                    
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Total procesadas", len(results))
                    col2.metric("Encontradas", found_count)
                    col3.metric("No encontradas", not_found_count)
                    
                    # Mostrar tabla de resultados
                    st.subheader("Resultados:")
                    for result in results:
                        with st.expander(f"🎵 {result['track']} - {result['artist']}"):
                            st.write(f"**Álbum:** {result['album']}")
                            if result['youtube_link'] == "NO ENCONTRADO":
                                st.error("❌ No se encontró enlace")
                            elif result['youtube_link'].startswith("ERROR"):
                                st.error(f"❌ {result['youtube_link']}")
                            else:
                                st.success(f"✅ [Ver en YouTube]({result['youtube_link']})")
        
            except json.JSONDecodeError:
                st.error("❌ Error: El archivo no es un JSON válido")
            except Exception as e:
                st.error(f"❌ Error procesando el archivo: {str(e)}")
    
    with tab2:
        st.header("Descargar MP3 desde JSON")
        st.write("Carga un archivo JSON con enlaces de YouTube para descargar como MP3")
        
        # FFmpeg check
        ffmpeg_installed = check_ffmpeg()
        if not ffmpeg_installed:
            st.error("❌ FFmpeg no está instalado")
            st.warning("""
            **Para descargar MP3 necesitas instalar FFmpeg:**
            
            **Opción 1 - Windows (Recomendado):**
            1. Ve a: https://github.com/BtbN/FFmpeg-Builds/releases
            2. Descarga: `ffmpeg-master-latest-win64-gpl.zip`
            3. Extrae a: `C:\\ffmpeg`
            4. Agrega `C:\\ffmpeg\\bin` al PATH del sistema
            5. Reinicia la aplicación
            
            **Opción 2 - Chocolatey:**
            ```
            choco install ffmpeg
            ```
            
            **Opción 3 - Scoop:**
            ```
            scoop install ffmpeg
            ```
            """)
            
            # Opción de descarga sin conversión
            st.info("💡 **Alternativa:** Puedes descargar como audio sin convertir a MP3")
            use_alternative = st.checkbox("Usar descarga alternativa (sin MP3)")
        else:
            st.success("✅ FFmpeg detectado correctamente")
            use_alternative = False
        
        # Upload JSON file with YouTube links
        download_file = st.file_uploader("Selecciona un archivo JSON con enlaces", type=['json'], key="download_json")
        
        # Folder selection
        st.subheader("📁 Seleccionar carpeta de destino")
        default_path = str(Path.home() / "Downloads" / "Music")
        download_path = st.text_input("Ruta de descarga:", value=default_path)
        
        # Create folder if it doesn't exist
        if download_path:
            try:
                os.makedirs(download_path, exist_ok=True)
                st.success(f"✅ Carpeta: {download_path}")
            except Exception as e:
                st.error(f"❌ Error creando carpeta: {str(e)}")
                download_path = None
        
        if download_file is not None and download_path:
            try:
                # Leer JSON con enlaces
                json_data = json.load(download_file)
                
                # Filtrar solo canciones con enlaces válidos
                valid_songs = [
                    song for song in json_data 
                    if song.get('youtube_link') and 
                    song['youtube_link'] != "NO ENCONTRADO" and 
                    not song['youtube_link'].startswith("ERROR") and
                    song['youtube_link'].startswith("https://www.youtube.com/watch?v=")
                ]
                
                st.success(f"Archivo cargado. Canciones válidas para descargar: {len(valid_songs)}")
                
                # Mostrar preview
                with st.expander("Vista previa de canciones a descargar"):
                    for song in valid_songs[:5]:
                        st.write(f"🎵 {song.get('track', 'N/A')} - {song.get('artist', 'N/A')}")
                        st.write(f"🔗 {song.get('youtube_link', 'N/A')}")
                        st.write("---")
                
                # Opciones de descarga
                col1, col2 = st.columns(2)
                with col1:
                    if ffmpeg_installed and not use_alternative:
                        quality = st.selectbox("Calidad de audio:", ["192", "128", "320"], index=0)
                        format_type = "MP3"
                    else:
                        quality = st.selectbox("Calidad de audio:", ["best", "worst"], index=0)
                        format_type = "Audio original"
                        
                with col2:
                    max_downloads = st.number_input("Máximo de descargas:", min_value=1, max_value=len(valid_songs), value=min(10, len(valid_songs)))
                
                st.info(f"📥 Formato de descarga: {format_type}")
                
                # Botón para iniciar descarga
                download_button_text = "⬇️ Iniciar descarga de MP3" if (ffmpeg_installed and not use_alternative) else "⬇️ Iniciar descarga de Audio"
                
                if st.button(download_button_text):
                    if not valid_songs:
                        st.error("❌ No hay canciones válidas para descargar")
                        return
                    
                    download_progress = st.progress(0)
                    download_status = st.empty()
                    
                    successful_downloads = 0
                    failed_downloads = 0
                    
                    songs_to_download = valid_songs[:max_downloads]
                    
                    for i, song in enumerate(songs_to_download):
                        try:
                            track_name = song.get('track', 'Unknown')
                            artist_name = song.get('artist', 'Unknown')
                            youtube_link = song.get('youtube_link', '')
                            
                            # Limpiar nombres de archivo
                            safe_artist = "".join(c for c in artist_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
                            safe_track = "".join(c for c in track_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
                            
                            download_status.text(f"Descargando: {track_name} - {artist_name}")
                            
                            # Configurar yt-dlp según disponibilidad de FFmpeg
                            if ffmpeg_installed and not use_alternative:
                                # Configuración para MP3 con FFmpeg
                                ydl_opts = {
                                    'format': 'bestaudio/best',
                                    'outtmpl': os.path.join(download_path, f'{safe_artist} - {safe_track}.%(ext)s'),
                                    'postprocessors': [{
                                        'key': 'FFmpegExtractAudio',
                                        'preferredcodec': 'mp3',
                                        'preferredquality': quality,
                                    }],
                                    'quiet': True,
                                    'no_warnings': True,
                                }
                            else:
                                # Configuración sin FFmpeg (audio original)
                                ydl_opts = {
                                    'format': f'bestaudio[ext=m4a]/bestaudio/best' if quality == 'best' else 'worstaudio',
                                    'outtmpl': os.path.join(download_path, f'{safe_artist} - {safe_track}.%(ext)s'),
                                    'quiet': True,
                                    'no_warnings': True,
                                }
                            
                            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                                ydl.download([youtube_link])
                                successful_downloads += 1
                                
                        except Exception as e:
                            failed_downloads += 1
                            st.error(f"❌ Error descargando {track_name}: {str(e)}")
                        
                        # Actualizar progreso
                        progress = (i + 1) / len(songs_to_download)
                        download_progress.progress(progress)
                    
                    # Mostrar resultados finales
                    download_status.text("✅ Descarga completada!")
                    
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Exitosas", successful_downloads)
                    col2.metric("Fallidas", failed_downloads)
                    col3.metric("Total", len(songs_to_download))
                    
                    st.success(f"🎵 Descargas completadas en: {download_path}")
                    
                    if not ffmpeg_installed or use_alternative:
                        st.info("""
                        📝 **Nota:** Los archivos se descargaron en formato de audio original.
                        Para convertir a MP3, instala FFmpeg y usa la descarga normal.
                        """)
                    
            except json.JSONDecodeError:
                st.error("❌ Error: El archivo no es un JSON válido")
            except Exception as e:
                st.error(f"❌ Error procesando el archivo: {str(e)}")
    
    # Instrucciones actualizadas
    with st.sidebar:
        st.header("📋 Instrucciones")
        st.write("""
        ## 🔍 Buscar Enlaces:
        1. **Formato del JSON:** Lista de objetos con:
           - `Track Name`
           - `Album Name` 
           - `Artist Name(s)`
        
        2. **Proceso:** Busca automáticamente cada canción en YouTube
        
        3. **Descargas:** Cada 5% del progreso podrás descargar JSON y TXT
        
        ## ⬇️ Descargar MP3:
        1. **Archivo JSON:** Usa un JSON generado con enlaces de YouTube
        
        2. **Carpeta:** Selecciona donde guardar los archivos
        
        3. **FFmpeg:** Necesario para MP3, opcional para audio original
        
        **Ejemplo JSON:**
        ```json
        [
          {
            "track": "Bohemian Rhapsody",
            "album": "A Night at the Opera",
            "artist": "Queen",
            "youtube_link": "https://www.youtube.com/watch?v=..."
          }
        ]
        """)
        
        st.header("🔧 Instalación FFmpeg")
        st.write("""
        **Windows:**
        1. Descarga desde: [FFmpeg Builds](https://github.com/BtbN/FFmpeg-Builds/releases)
        2. Extrae a `C:\\ffmpeg`
        3. Agrega `C:\\ffmpeg\\bin` al PATH
        4. Reinicia la app
        
        **Verificar instalación:**
        Abre CMD y ejecuta: `ffmpeg -version`
        """)
        
        st.header("⚠️ Importante")
        st.write("""
        - Sin FFmpeg: descarga audio original
        - Con FFmpeg: convierte a MP3
        - Respeta derechos de autor
        - Solo uso personal
        """)

if __name__ == "__main__":
    main()

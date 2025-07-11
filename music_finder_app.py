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
    tab1, tab2, tab3, tab4 = st.tabs(["🔍 Buscar Enlaces", "⬇️ Descargar MP3", "📋 Descarga Masiva", "📹 Descargar Video"])
    
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
    
    with tab3:
        st.header("Descarga Masiva de Enlaces")
        st.write("Pega enlaces de YouTube directamente para descargar en lote")
        
        # FFmpeg check for bulk download
        ffmpeg_installed = check_ffmpeg()
        if not ffmpeg_installed:
            st.error("❌ FFmpeg no está instalado")
            st.info("💡 **Alternativa:** Puedes descargar como audio sin convertir a MP3")
            use_alternative_bulk = st.checkbox("Usar descarga alternativa (sin MP3)", key="bulk_alt")
        else:
            st.success("✅ FFmpeg detectado correctamente")
            use_alternative_bulk = False
        
        # Text area for pasting links
        st.subheader("📝 Enlaces de YouTube")
        links_text = st.text_area(
            "Pega los enlaces aquí (uno por línea):",
            height=200,
            placeholder="https://www.youtube.com/watch?v=dQw4w9WgXcQ\nhttps://www.youtube.com/watch?v=...\nhttps://www.youtube.com/watch?v=...",
            key="bulk_links"
        )
        
        # Process links
        if links_text:
            # Parse links
            raw_links = [link.strip() for link in links_text.split('\n') if link.strip()]
            valid_links = []
            
            for link in raw_links:
                if 'youtube.com/watch?v=' in link or 'youtu.be/' in link:
                    # Normalize YouTube links
                    if 'youtu.be/' in link:
                        video_id = link.split('youtu.be/')[-1].split('?')[0]
                        normalized_link = f"https://www.youtube.com/watch?v={video_id}"
                    else:
                        normalized_link = link
                    valid_links.append(normalized_link)
            
            st.success(f"Enlaces válidos encontrados: {len(valid_links)}")
            
            if valid_links:
                with st.expander("Vista previa de enlaces"):
                    for i, link in enumerate(valid_links[:10], 1):
                        st.write(f"{i}. {link}")
                    if len(valid_links) > 10:
                        st.write(f"... y {len(valid_links) - 10} más")
        
        # Folder selection for bulk download
        st.subheader("📁 Seleccionar carpeta de destino")
        default_path_bulk = str(Path.home() / "Downloads" / "Music" / "Bulk")
        download_path_bulk = st.text_input("Ruta de descarga:", value=default_path_bulk, key="bulk_path")
        
        # Create folder if it doesn't exist
        if download_path_bulk:
            try:
                os.makedirs(download_path_bulk, exist_ok=True)
                st.success(f"✅ Carpeta: {download_path_bulk}")
            except Exception as e:
                st.error(f"❌ Error creando carpeta: {str(e)}")
                download_path_bulk = None
        
        # Bulk download options
        if links_text and valid_links and download_path_bulk:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if ffmpeg_installed and not use_alternative_bulk:
                    quality_bulk = st.selectbox("Calidad de audio:", ["192", "128", "320"], index=0, key="bulk_quality")
                    format_type_bulk = "MP3"
                else:
                    quality_bulk = st.selectbox("Calidad de audio:", ["best", "worst"], index=0, key="bulk_quality_alt")
                    format_type_bulk = "Audio original"
            
            with col2:
                max_downloads_bulk = st.number_input(
                    "Máximo de descargas:", 
                    min_value=1, 
                    max_value=len(valid_links), 
                    value=min(len(valid_links), 20),
                    key="bulk_max"
                )
            
            with col3:
                # Naming options
                naming_option = st.selectbox(
                    "Formato de nombre:",
                    ["Título del video", "Numerado secuencial"],
                    key="bulk_naming"
                )
            
            st.info(f"📥 Formato de descarga: {format_type_bulk}")
            
            # Start bulk download
            download_button_text_bulk = "⬇️ Iniciar descarga masiva MP3" if (ffmpeg_installed and not use_alternative_bulk) else "⬇️ Iniciar descarga masiva Audio"
            
            if st.button(download_button_text_bulk):
                if not valid_links:
                    st.error("❌ No hay enlaces válidos para descargar")
                    return
                
                bulk_progress = st.progress(0)
                bulk_status = st.empty()
                
                successful_bulk = 0
                failed_bulk = 0
                
                links_to_download = valid_links[:max_downloads_bulk]
                
                for i, youtube_link in enumerate(links_to_download):
                    try:
                        bulk_status.text(f"Descargando {i+1}/{len(links_to_download)}: {youtube_link}")
                        
                        # Configure filename based on naming option
                        if naming_option == "Numerado secuencial":
                            filename_template = f"{i+1:03d}_%(title)s.%(ext)s"
                        else:
                            filename_template = "%(title)s.%(ext)s"
                        
                        # Configure yt-dlp for bulk download
                        if ffmpeg_installed and not use_alternative_bulk:
                            # MP3 configuration with FFmpeg
                            ydl_opts_bulk = {
                                'format': 'bestaudio/best',
                                'outtmpl': os.path.join(download_path_bulk, filename_template),
                                'postprocessors': [{
                                    'key': 'FFmpegExtractAudio',
                                    'preferredcodec': 'mp3',
                                    'preferredquality': quality_bulk,
                                }],
                                'quiet': True,
                                'no_warnings': True,
                            }
                        else:
                            # Configuration without FFmpeg (original audio)
                            ydl_opts_bulk = {
                                'format': f'bestaudio[ext=m4a]/bestaudio/best' if quality_bulk == 'best' else 'worstaudio',
                                'outtmpl': os.path.join(download_path_bulk, filename_template),
                                'quiet': True,
                                'no_warnings': True,
                            }
                        
                        with yt_dlp.YoutubeDL(ydl_opts_bulk) as ydl:
                            ydl.download([youtube_link])
                            successful_bulk += 1
                            
                    except Exception as e:
                        failed_bulk += 1
                        st.error(f"❌ Error descargando {youtube_link}: {str(e)}")
                    
                    # Update progress
                    progress_bulk = (i + 1) / len(links_to_download)
                    bulk_progress.progress(progress_bulk)
                
                # Show final results
                bulk_status.text("✅ Descarga masiva completada!")
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Exitosas", successful_bulk)
                col2.metric("Fallidas", failed_bulk)
                col3.metric("Total", len(links_to_download))
                
                st.success(f"🎵 Descarga masiva completada en: {download_path_bulk}")
                
                if not ffmpeg_installed or use_alternative_bulk:
                    st.info("""
                    📝 **Nota:** Los archivos se descargaron en formato de audio original.
                    Para convertir a MP3, instala FFmpeg y usa la descarga normal.
                    """)
    
    with tab4:
        st.header("📹 Descargar Videos de YouTube")
        st.write("Descarga videos de YouTube en diferentes calidades y formatos")
        
        # Input methods
        input_method = st.radio(
            "Método de entrada:",
            ["📝 Enlaces individuales", "📋 Enlaces múltiples"],
            key="video_input_method"
        )
        
        video_urls = []
        
        if input_method == "📝 Enlaces individuales":
            # Single URL input
            single_url = st.text_input(
                "Enlace de YouTube:",
                placeholder="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                key="single_video_url"
            )
            if single_url and ('youtube.com/watch?v=' in single_url or 'youtu.be/' in single_url):
                # Normalize URL
                if 'youtu.be/' in single_url:
                    video_id = single_url.split('youtu.be/')[-1].split('?')[0]
                    normalized_url = f"https://www.youtube.com/watch?v={video_id}"
                else:
                    normalized_url = single_url
                video_urls = [normalized_url]
                st.success("✅ Enlace válido")
        else:
            # Multiple URLs input
            multi_urls_text = st.text_area(
                "Enlaces de YouTube (uno por línea):",
                height=150,
                placeholder="https://www.youtube.com/watch?v=dQw4w9WgXcQ\nhttps://www.youtube.com/watch?v=...",
                key="multi_video_urls"
            )
            
            if multi_urls_text:
                raw_urls = [url.strip() for url in multi_urls_text.split('\n') if url.strip()]
                for url in raw_urls:
                    if 'youtube.com/watch?v=' in url or 'youtu.be/' in url:
                        if 'youtu.be/' in url:
                            video_id = url.split('youtu.be/')[-1].split('?')[0]
                            normalized_url = f"https://www.youtube.com/watch?v={video_id}"
                        else:
                            normalized_url = url
                        video_urls.append(normalized_url)
                
                if video_urls:
                    st.success(f"✅ {len(video_urls)} enlaces válidos encontrados")
        
        # Show video info and quality options if URLs are provided
        if video_urls:
            # Folder selection
            st.subheader("📁 Configuración de descarga")
            default_video_path = str(Path.home() / "Downloads" / "Videos")
            download_video_path = st.text_input("Carpeta de destino:", value=default_video_path, key="video_path")
            
            if download_video_path:
                try:
                    os.makedirs(download_video_path, exist_ok=True)
                    st.success(f"✅ Carpeta: {download_video_path}")
                except Exception as e:
                    st.error(f"❌ Error creando carpeta: {str(e)}")
                    download_video_path = None
            
            if download_video_path:
                # Get video info for quality selection (use first video as reference)
                if st.button("🔍 Obtener información de calidades disponibles", key="get_video_info"):
                    try:
                        with st.spinner("Obteniendo información del video..."):
                            ydl_opts = {
                                'quiet': True,
                                'no_warnings': True,
                            }
                            
                            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                                info = ydl.extract_info(video_urls[0], download=False)
                                
                                # Show video title
                                st.subheader(f"📹 {info.get('title', 'Título no disponible')}")
                                st.write(f"**Canal:** {info.get('uploader', 'N/A')}")
                                st.write(f"**Duración:** {info.get('duration', 0) // 60}:{info.get('duration', 0) % 60:02d}")
                                
                                # Process formats
                                formats = info.get('formats', [])
                                
                                # Video + Audio formats
                                video_audio_formats = []
                                video_only_formats = []
                                audio_only_formats = []
                                
                                for fmt in formats:
                                    if fmt.get('vcodec') != 'none' and fmt.get('acodec') != 'none':
                                        # Video + Audio
                                        height = fmt.get('height', 0)
                                        fps = fmt.get('fps', 0)
                                        ext = fmt.get('ext', 'unknown')
                                        filesize = fmt.get('filesize') or fmt.get('filesize_approx', 0)
                                        size_mb = f"{filesize / (1024*1024):.1f} MB" if filesize else "Tamaño desconocido"
                                        
                                        if height:
                                            format_desc = f"{height}p"
                                            if fps and fps > 30:
                                                format_desc += f" {fps}fps"
                                            format_desc += f" ({ext}) - {size_mb}"
                                            
                                            video_audio_formats.append({
                                                'format_id': fmt['format_id'],
                                                'description': format_desc,
                                                'height': height,
                                                'ext': ext
                                            })
                                    
                                    elif fmt.get('vcodec') != 'none' and fmt.get('acodec') == 'none':
                                        # Video only
                                        height = fmt.get('height', 0)
                                        fps = fmt.get('fps', 0)
                                        ext = fmt.get('ext', 'unknown')
                                        
                                        if height:
                                            format_desc = f"{height}p"
                                            if fps and fps > 30:
                                                format_desc += f" {fps}fps"
                                            format_desc += f" ({ext}) - Solo video"
                                            
                                            video_only_formats.append({
                                                'format_id': fmt['format_id'],
                                                'description': format_desc,
                                                'height': height
                                            })
                                    
                                    elif fmt.get('acodec') != 'none' and fmt.get('vcodec') == 'none':
                                        # Audio only
                                        abr = fmt.get('abr', 0)
                                        ext = fmt.get('ext', 'unknown')
                                        
                                        if abr:
                                            format_desc = f"{abr}kbps ({ext}) - Solo audio"
                                            audio_only_formats.append({
                                                'format_id': fmt['format_id'],
                                                'description': format_desc,
                                                'abr': abr
                                            })
                                
                                # Sort formats
                                video_audio_formats.sort(key=lambda x: x['height'], reverse=True)
                                video_only_formats.sort(key=lambda x: x['height'], reverse=True)
                                audio_only_formats.sort(key=lambda x: x['abr'], reverse=True)
                                
                                # Display format options
                                st.subheader("🎯 Seleccionar formato de descarga")
                                
                                download_type = st.radio(
                                    "Tipo de descarga:",
                                    ["📹 Video + Audio", "🎬 Solo Video", "🎵 Solo Audio", "🔧 Personalizado"],
                                    key="download_type"
                                )
                                
                                selected_format = None
                                
                                if download_type == "📹 Video + Audio":
                                    if video_audio_formats:
                                        format_options = [f"{fmt['description']}" for fmt in video_audio_formats]
                                        selected_idx = st.selectbox(
                                            "Calidad:",
                                            range(len(format_options)),
                                            format_func=lambda x: format_options[x],
                                            key="video_audio_quality"
                                        )
                                        selected_format = video_audio_formats[selected_idx]['format_id']
                                    else:
                                        st.warning("No hay formatos de video+audio disponibles")
                                
                                elif download_type == "🎬 Solo Video":
                                    if video_only_formats:
                                        format_options = [f"{fmt['description']}" for fmt in video_only_formats]
                                        selected_idx = st.selectbox(
                                            "Calidad:",
                                            range(len(format_options)),
                                            format_func=lambda x: format_options[x],
                                            key="video_only_quality"
                                        )
                                        selected_format = video_only_formats[selected_idx]['format_id']
                                        st.info("⚠️ Este formato no incluye audio")
                                    else:
                                        st.warning("No hay formatos de solo video disponibles")
                                
                                elif download_type == "🎵 Solo Audio":
                                    if audio_only_formats:
                                        format_options = [f"{fmt['description']}" for fmt in audio_only_formats]
                                        selected_idx = st.selectbox(
                                            "Calidad:",
                                            range(len(format_options)),
                                            format_func=lambda x: format_options[x],
                                            key="audio_only_quality"
                                        )
                                        selected_format = audio_only_formats[selected_idx]['format_id']
                                    else:
                                        st.warning("No hay formatos de solo audio disponibles")
                                
                                else:  # Personalizado
                                    st.write("**Formatos disponibles:**")
                                    
                                    # Show all formats in expandable sections
                                    if video_audio_formats:
                                        with st.expander("📹 Video + Audio"):
                                            for fmt in video_audio_formats:
                                                st.write(f"• {fmt['description']} (ID: {fmt['format_id']})")
                                    
                                    if video_only_formats:
                                        with st.expander("🎬 Solo Video"):
                                            for fmt in video_only_formats:
                                                st.write(f"• {fmt['description']} (ID: {fmt['format_id']})")
                                    
                                    if audio_only_formats:
                                        with st.expander("🎵 Solo Audio"):
                                            for fmt in audio_only_formats:
                                                st.write(f"• {fmt['description']} (ID: {fmt['format_id']})")
                                    
                                    custom_format = st.text_input(
                                        "ID de formato personalizado:",
                                        placeholder="Ej: 137+140 (video+audio) o best",
                                        key="custom_format"
                                    )
                                    if custom_format:
                                        selected_format = custom_format
                                
                                # Download options
                                if selected_format:
                                    st.subheader("⚙️ Opciones adicionales")
                                    
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        subtitle_option = st.checkbox("Descargar subtítulos", key="download_subs")
                                        thumbnail_option = st.checkbox("Descargar miniatura", key="download_thumb")
                                    
                                    with col2:
                                        if len(video_urls) > 1:
                                            max_video_downloads = st.number_input(
                                                "Máximo de videos a descargar:",
                                                min_value=1,
                                                max_value=len(video_urls),
                                                value=min(5, len(video_urls)),
                                                key="max_video_downloads"
                                            )
                                        else:
                                            max_video_downloads = 1
                                    
                                    # Start download
                                    download_button_text = f"⬇️ Descargar {len(video_urls[:max_video_downloads])} video(s)"
                                    
                                    if st.button(download_button_text, key="start_video_download"):
                                        video_progress = st.progress(0)
                                        video_status = st.empty()
                                        
                                        successful_video_downloads = 0
                                        failed_video_downloads = 0
                                        
                                        videos_to_download = video_urls[:max_video_downloads]
                                        
                                        for i, video_url in enumerate(videos_to_download):
                                            try:
                                                video_status.text(f"Descargando video {i+1}/{len(videos_to_download)}")
                                                
                                                # Configure yt-dlp options
                                                ydl_opts_video = {
                                                    'format': selected_format,
                                                    'outtmpl': os.path.join(download_video_path, '%(title)s.%(ext)s'),
                                                    'quiet': True,
                                                    'no_warnings': True,
                                                }
                                                
                                                # Add subtitle options
                                                if subtitle_option:
                                                    ydl_opts_video.update({
                                                        'writesubtitles': True,
                                                        'writeautomaticsub': True,
                                                        'subtitleslangs': ['es', 'en'],
                                                    })
                                                
                                                # Add thumbnail option
                                                if thumbnail_option:
                                                    ydl_opts_video['writethumbnail'] = True
                                                
                                                # Merge video+audio if needed (for separate streams)
                                                if '+' in selected_format or (download_type == "🎬 Solo Video" and 
                                                    st.checkbox("Intentar combinar con audio", key=f"merge_audio_{i}")):
                                                    ydl_opts_video['postprocessors'] = [{
                                                        'key': 'FFmpegVideoConvertor',
                                                        'preferedformat': 'mp4',
                                                    }]
                                                
                                                with yt_dlp.YoutubeDL(ydl_opts_video) as ydl:
                                                    ydl.download([video_url])
                                                    successful_video_downloads += 1
                                                
                                            except Exception as e:
                                                failed_video_downloads += 1
                                                st.error(f"❌ Error descargando video {i+1}: {str(e)}")
                                            
                                            # Update progress
                                            progress_video = (i + 1) / len(videos_to_download)
                                            video_progress.progress(progress_video)
                                        
                                        # Show final results
                                        video_status.text("✅ Descarga de videos completada!")
                                        
                                        col1, col2, col3 = st.columns(3)
                                        col1.metric("Exitosas", successful_video_downloads)
                                        col2.metric("Fallidas", failed_video_downloads)
                                        col3.metric("Total", len(videos_to_download))
                                        
                                        st.success(f"📹 Videos descargados en: {download_video_path}")
                    
                    except Exception as e:
                        st.error(f"❌ Error obteniendo información del video: {str(e)}")
        
        # Instructions for video download
        with st.expander("📖 Instrucciones para descarga de videos"):
            st.write("""
            ### 🎯 Tipos de descarga:
            
            **📹 Video + Audio:** Descarga completa con video y audio sincronizados
            - Mejor para ver videos normalmente
            - Archivo único con todo incluido
            
            **🎬 Solo Video:** Descarga únicamente la pista de video
            - Útil para análisis visual o edición
            - No incluye audio
            
            **🎵 Solo Audio:** Descarga únicamente la pista de audio
            - Similar al modo MP3 pero con más opciones de calidad
            - Ideal para música o podcasts
            
            **🔧 Personalizado:** Especifica formatos manualmente
            - Para usuarios avanzados
            - Ejemplos: `137+140` (1080p video + audio), `best[height<=720]`
            
            ### 📊 Calidades comunes:
            - **4K (2160p):** Máxima calidad, archivos grandes
            - **1080p:** Full HD, buen balance calidad/tamaño
            - **720p:** HD, archivos medianos
            - **480p/360p:** Menor calidad, archivos pequeños
            
            ### ⚙️ Opciones adicionales:
            - **Subtítulos:** Descarga subtítulos en español e inglés
            - **Miniatura:** Descarga la imagen de portada del video
            - **Descarga múltiple:** Procesa varios videos en lote
            """)
    
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
        
        ## 📋 Descarga Masiva:
        1. **Enlaces:** Pega enlaces de YouTube (uno por línea)
        
        2. **Formatos aceptados:**
           - `https://www.youtube.com/watch?v=...`
           - `https://youtu.be/...`
        
        3. **Opciones:** Elige calidad y formato de nombres
        
        ## 📹 Descargar Video:
        1. **Enlaces:** Individual o múltiples URLs de YouTube
        
        2. **Calidades:** Desde 360p hasta 4K (según disponibilidad)
        
        3. **Formatos:** Video+Audio, Solo Video, Solo Audio, Personalizado
        
        4. **Extras:** Subtítulos, miniaturas, descarga en lote
        
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
        ```
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
        - Descarga masiva: máx 20 por defecto
        """)

if __name__ == "__main__":
    main()

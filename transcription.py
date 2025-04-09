#!/usr/bin/env python3
"""
Outil de transcription pour fichiers audio très longs (optimisé pour 13+ heures)
Compatible avec macOS Apple Silicon et autres plateformes
Auteur: Claude
Date: 2025-04-06
"""

import os
import argparse
import subprocess
import json
import time
import tempfile
import shutil
import requests
from datetime import datetime

# Configuration - À modifier selon vos besoins
CONFIG = {
    "chunk_duration": 10,     # Durée des segments en minutes
    "output_folder": "transcriptions",  # Dossier pour les sorties
    "temp_folder": "temp_audio",  # Dossier temporaire
    "whisper_model": "tiny",  # Options: tiny, base, small, medium, large
    "parallel_jobs": 1,       # Nombre de transcriptions en parallèle (1 pour fiabilité)
    "api_service": "local"    # Options: local, assemblyai, openai
}

# Constantes
WHISPER_MODELS = {
    "tiny": {"ram": "1GB", "speed": "très rapide", "qualité": "basique"},
    "base": {"ram": "1GB", "speed": "rapide", "qualité": "acceptable"},
    "small": {"ram": "2GB", "speed": "modéré", "qualité": "bonne"},
    "medium": {"ram": "5GB", "speed": "lent", "qualité": "très bonne"},
    "large": {"ram": "10GB", "speed": "très lent", "qualité": "excellente"}
}

# Configuration des API (à remplacer par vos propres clés)
API_KEYS = {
    "assemblyai": "VOTRE_CLE_API_ASSEMBLY_AI",
    "openai": "VOTRE_CLE_API_OPENAI"
}

def check_dependencies():
    """Vérifie que toutes les dépendances nécessaires sont installées"""
    missing = []
    
    # Vérifier FFmpeg
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    except (subprocess.SubprocessError, FileNotFoundError):
        missing.append("FFmpeg")
    
    # Vérifier Whisper si mode local
    if CONFIG["api_service"] == "local":
        try:
            import whisper
        except ImportError:
            missing.append("OpenAI Whisper")
    
    if missing:
        print("⚠️ Dépendances manquantes:")
        for dep in missing:
            if dep == "FFmpeg":
                print("  - FFmpeg: installez avec 'brew install ffmpeg' sur macOS")
                print("            ou 'apt install ffmpeg' sur Ubuntu/Debian")
            elif dep == "OpenAI Whisper":
                print("  - OpenAI Whisper: installez avec 'pip install -U openai-whisper'")
                print("    Note: Assurez-vous d'avoir Pytorch installé")
                
        print("\nInstallation recommandée sur macOS:")
        print("  brew install ffmpeg")
        print("  pip install -U openai-whisper torch")
        
        return False
    
    # Vérifier si le répertoire temporaire existe déjà
    if os.path.exists(CONFIG["temp_folder"]):
        print(f"⚠️ Le dossier temporaire {CONFIG['temp_folder']} existe déjà.")
        print("   Il contient peut-être des fichiers d'une exécution précédente.")
        try:
            # Essayer de nettoyer les fichiers wav
            for file in os.listdir(CONFIG["temp_folder"]):
                if file.endswith(".wav"):
                    os.remove(os.path.join(CONFIG["temp_folder"], file))
            print("✅ Nettoyage des fichiers temporaires effectué.")
        except Exception as e:
            print(f"⚠️ Impossible de nettoyer certains fichiers: {e}")
            print("   Vous pouvez essayer de supprimer manuellement ce dossier.")
    
    return True

def get_audio_duration(audio_file):
    """Obtient la durée d'un fichier audio en secondes en utilisant FFmpeg"""
    cmd = ["ffmpeg", "-i", audio_file, "-f", "null", "-"]
    result = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    
    # Extraire la durée du résultat
    import re
    duration_match = re.search(r"Duration: (\d{2}):(\d{2}):(\d{2})\.(\d{2})", result.stderr)
    
    if not duration_match:
        raise ValueError("Impossible de déterminer la durée du fichier audio")
    
    hours, minutes, seconds, centiseconds = map(int, duration_match.groups())
    total_seconds = hours * 3600 + minutes * 60 + seconds + centiseconds / 100
    
    return total_seconds

def format_time(seconds):
    """Formate un temps en secondes en format heures:minutes:secondes"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"

def split_audio(audio_file, chunk_duration_min=10, temp_folder="temp_audio"):
    """
    Divise un fichier audio en segments de durée spécifiée
    
    Args:
        audio_file: Chemin vers le fichier audio
        chunk_duration_min: Durée de chaque segment en minutes
        temp_folder: Dossier pour les fichiers temporaires
    
    Returns:
        Liste des chemins vers les segments audio
    """
    # Créer le dossier temporaire s'il n'existe pas
    os.makedirs(temp_folder, exist_ok=True)
    
    # Obtenir la durée totale du fichier
    total_duration = get_audio_duration(audio_file)
    total_duration_formatted = format_time(total_duration)
    print(f"📊 Durée totale du fichier: {total_duration_formatted} ({total_duration:.1f} secondes)")
    
    # Calculer le nombre de segments
    chunk_duration_sec = chunk_duration_min * 60
    num_chunks = int(total_duration / chunk_duration_sec) + 1
    
    # Préparer la liste pour stocker les chemins des segments
    chunk_files = []
    
    # Extraire les segments
    for i in range(num_chunks):
        start_time = i * chunk_duration_sec
        
        # Si c'est le dernier segment, ajuster la durée
        if i == num_chunks - 1:
            duration = total_duration - start_time
        else:
            duration = chunk_duration_sec
        
        # Formater les temps pour FFmpeg
        start_time_fmt = format_time(start_time)
        duration_fmt = format_time(duration)
        
        # Préparer le nom du fichier de sortie
        output_filename = os.path.join(
            temp_folder, 
            f"segment_{i:04d}_{start_time_fmt.replace(':', '-')}.wav"
        )
        
        # Extraire le segment avec FFmpeg
        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-ss", start_time_fmt, 
            "-i", audio_file, 
            "-t", duration_fmt,
            "-ac", "1",  # Mono pour une meilleure reconnaissance
            "-ar", "16000",  # Fréquence d'échantillonnage de 16kHz
            output_filename
        ]
        
        # Afficher la progression
        progress = (i / num_chunks) * 100
        print(f"⏳ Préparation du segment {i+1}/{num_chunks} ({progress:.1f}%) - {start_time_fmt} à {format_time(start_time + duration)}")
        
        # Exécuter la commande FFmpeg
        subprocess.run(cmd, check=True)
        
        # Ajouter le chemin du fichier à la liste
        chunk_files.append(output_filename)
    
    print(f"✅ Fichier audio divisé en {len(chunk_files)} segments")
    return chunk_files

def transcribe_segment_local(audio_file, language="fr"):
    """
    Transcrit un segment audio en utilisant Whisper localement
    
    Args:
        audio_file: Chemin vers le fichier audio à transcrire
        language: Code de langue (ex: fr, en)
    
    Returns:
        Texte transcrit
    """
    import whisper
    
    print(f"🔄 Chargement du modèle Whisper ({CONFIG['whisper_model']})...")
    model = whisper.load_model(CONFIG['whisper_model'])
    
    print(f"🔄 Transcription en cours: {os.path.basename(audio_file)}")
    result = model.transcribe(
        audio_file, 
        language=language,
        fp16=False  # Désactiver fp16 pour éviter les problèmes sur certains macOS
    )
    
    return result["text"]

def transcribe_segment_assemblyai(audio_file, language="fr"):
    """
    Transcrit un segment audio en utilisant l'API Assembly AI
    
    Args:
        audio_file: Chemin vers le fichier audio à transcrire
        language: Code de langue (ex: fr, en)
    
    Returns:
        Texte transcrit
    """
    api_key = API_KEYS["assemblyai"]
    if api_key == "VOTRE_CLE_API_ASSEMBLY_AI":
        print("⚠️ Veuillez configurer votre clé API Assembly AI dans le script")
        return ""
    
    headers = {
        "authorization": api_key,
        "content-type": "application/json"
    }
    
    # Lire le fichier audio
    print(f"🔄 Préparation du fichier pour Assembly AI: {os.path.basename(audio_file)}")
    with open(audio_file, "rb") as f:
        audio_data = f.read()
    
    # Télécharger le fichier audio
    upload_url = "https://api.assemblyai.com/v2/upload"
    print("🔄 Téléversement du fichier audio...")
    upload_response = requests.post(upload_url, headers=headers, data=audio_data)
    
    if upload_response.status_code != 200:
        print(f"❌ Erreur lors du téléversement: {upload_response.text}")
        return ""
    
    audio_url = upload_response.json()["upload_url"]
    
    # Transcrire l'audio
    transcript_url = "https://api.assemblyai.com/v2/transcript"
    transcript_request = {
        "audio_url": audio_url,
        "language_code": language
    }
    
    print("🔄 Demande de transcription...")
    transcript_response = requests.post(transcript_url, json=transcript_request, headers=headers)
    
    if transcript_response.status_code != 200:
        print(f"❌ Erreur lors de la demande de transcription: {transcript_response.text}")
        return ""
    
    transcript_id = transcript_response.json()["id"]
    
    # Attendre la transcription
    print("⏳ Attente de la transcription...")
    while True:
        transcript_status_url = f"https://api.assemblyai.com/v2/transcript/{transcript_id}"
        transcript_status = requests.get(transcript_status_url, headers=headers).json()
        
        if transcript_status["status"] == "completed":
            print("✅ Transcription terminée!")
            return transcript_status["text"]
        elif transcript_status["status"] == "error":
            print(f"❌ Erreur de transcription: {transcript_status['error']}")
            return ""
        
        print("⏳ Transcription en cours...")
        time.sleep(5)

def transcribe_segment_openai(audio_file, language="fr"):
    """
    Transcrit un segment audio en utilisant l'API Whisper d'OpenAI
    
    Args:
        audio_file: Chemin vers le fichier audio à transcrire
        language: Code de langue (ex: fr, en)
    
    Returns:
        Texte transcrit
    """
    api_key = API_KEYS["openai"]
    if api_key == "VOTRE_CLE_API_OPENAI":
        print("⚠️ Veuillez configurer votre clé API OpenAI dans le script")
        return ""
    
    from openai import OpenAI
    
    client = OpenAI(api_key=api_key)
    
    print(f"🔄 Envoi du fichier à l'API OpenAI: {os.path.basename(audio_file)}")
    with open(audio_file, "rb") as audio_data:
        response = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_data,
            language=language
        )
    
    return response.text

def transcribe_segment(audio_file, language="fr"):
    """
    Transcrit un segment audio en utilisant le service configuré
    
    Args:
        audio_file: Chemin vers le fichier audio à transcrire
        language: Code de langue (ex: fr, en)
    
    Returns:
        Texte transcrit
    """
    if CONFIG["api_service"] == "local":
        return transcribe_segment_local(audio_file, language)
    elif CONFIG["api_service"] == "assemblyai":
        return transcribe_segment_assemblyai(audio_file, language)
    elif CONFIG["api_service"] == "openai":
        return transcribe_segment_openai(audio_file, language)
    else:
        raise ValueError(f"Service de transcription non reconnu: {CONFIG['api_service']}")

def process_file(audio_file, language="fr", output_file=None):
    """
    Processus principal pour traiter un fichier audio et le transcrire
    
    Args:
        audio_file: Chemin vers le fichier audio à transcrire
        language: Code de langue pour la transcription
        output_file: Fichier de sortie pour la transcription (optionnel)
    
    Returns:
        Chemin vers le fichier de transcription
    """
    start_time = time.time()
    
    # Créer le dossier de sortie s'il n'existe pas
    os.makedirs(CONFIG["output_folder"], exist_ok=True)
    
    # Si aucun fichier de sortie n'est spécifié, en créer un
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(
            CONFIG["output_folder"],
            f"transcription_{os.path.basename(audio_file).split('.')[0]}_{timestamp}.txt"
        )
    
    # S'assurer que le fichier de sortie est dans un dossier existant
    os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
    
    # Créer un fichier de journalisation
    log_file = output_file.replace(".txt", "_log.txt")
    
    # Journaliser la configuration
    with open(log_file, "w", encoding="utf-8") as f:
        f.write(f"Transcription de {audio_file}\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Langue: {language}\n")
        f.write(f"Configuration: {json.dumps(CONFIG, indent=2)}\n\n")
    
    print(f"🚀 Démarrage de la transcription pour: {audio_file}")
    print(f"📋 La transcription sera enregistrée dans: {output_file}")
    
    try:
        # Diviser le fichier audio en segments
        print(f"✂️ Division du fichier en segments de {CONFIG['chunk_duration']} minutes...")
        segments = split_audio(audio_file, CONFIG['chunk_duration'], CONFIG['temp_folder'])
        
        # Traiter chaque segment
        all_text = ""
        
        for i, segment in enumerate(segments):
            segment_name = os.path.basename(segment)
            segment_progress = f"({i+1}/{len(segments)})"
            
            print(f"\n🔤 Transcription du segment {segment_progress}: {segment_name}")
            
            # Transcrire le segment
            segment_text = transcribe_segment(segment, language)
            
            # Ajouter un séparateur pour indiquer le début d'un nouveau segment
            if i > 0:
                all_text += "\n\n--- Nouveau segment ---\n\n"
            
            all_text += segment_text
            
            # Enregistrer le texte transcrit dans le fichier de sortie
            # (sauvegarde incrémentielle pour éviter la perte de données)
            with open(output_file, "a", encoding="utf-8") as f:
                if i == 0:
                    f.write(segment_text)
                else:
                    f.write("\n\n--- Nouveau segment ---\n\n" + segment_text)
            
            # Mettre à jour le fichier journal
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"Segment {i+1}/{len(segments)} traité: {segment_name}\n")
                f.write(f"Heure: {datetime.now().strftime('%H:%M:%S')}\n\n")
            
            # Calculer et afficher la progression globale
            progress = ((i + 1) / len(segments)) * 100
            elapsed_time = time.time() - start_time
            estimated_total = (elapsed_time / (i + 1)) * len(segments)
            remaining_time = estimated_total - elapsed_time
            
            print(f"⏳ Progression: {progress:.1f}% - Temps écoulé: {format_time(elapsed_time)}")
            print(f"⏱️ Temps restant estimé: {format_time(remaining_time)}")
        
        # Nettoyage des fichiers temporaires
        print("\n🧹 Nettoyage des fichiers temporaires...")
        for segment in segments:
            if os.path.exists(segment):
                os.remove(segment)
        
        try:
            os.rmdir(CONFIG["temp_folder"])
        except:
            print(f"⚠️ Impossible de supprimer le dossier temporaire {CONFIG['temp_folder']}")
        
        # Finaliser le journal
        elapsed_time = time.time() - start_time
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"\nTranscription terminée en {format_time(elapsed_time)}\n")
        
        print(f"\n✅ Transcription terminée en {format_time(elapsed_time)}")
        print(f"📋 Résultat enregistré dans: {output_file}")
        
        return output_file
        
    except Exception as e:
        # En cas d'erreur, enregistrer l'erreur dans le journal
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"\nERREUR: {str(e)}\n")
        
        print(f"\n❌ Erreur lors de la transcription: {str(e)}")
        raise

def fix_ssl_certificates_macos():
    """Résout le problème de certificats SSL sur macOS"""
    import platform
    import subprocess
    
    if platform.system() != "Darwin":  # Seulement sur macOS
        return
    
    print("🔧 Vérification des certificats SSL sur macOS...")
    
    # Vérifier si les certificats Python existent déjà
    import ssl
    try:
        ssl.get_default_verify_paths()
        # Tester une connexion simple
        import urllib.request
        urllib.request.urlopen("https://www.google.com")
        print("✅ Les certificats SSL semblent correctement configurés.")
        return
    except ssl.SSLError:
        print("⚠️ Problème de certificats SSL détecté.")
    except Exception as e:
        if "CERTIFICATE_VERIFY_FAILED" in str(e):
            print("⚠️ Problème de certificats SSL détecté.")
        else:
            print(f"⚠️ Autre problème de connexion détecté: {e}")
    
    # Trouver l'emplacement du script Install Certificates.command
    import sys
    python_dir = sys.exec_prefix
    cert_script = os.path.join(python_dir, "Install Certificates.command")
    
    if os.path.exists(cert_script):
        print("🔧 Installation des certificats macOS pour Python...")
        try:
            subprocess.run(["/bin/bash", cert_script], check=True)
            print("✅ Certificats installés avec succès.")
        except subprocess.SubprocessError as e:
            print(f"⚠️ Échec de l'installation des certificats: {e}")
            print("⚠️ Désactivation temporaire de la vérification SSL...")
            # Désactiver temporairement la vérification SSL (non recommandé en production)
            ssl._create_default_https_context = ssl._create_unverified_context
    else:
        print("⚠️ Script d'installation des certificats introuvable.")
        print("⚠️ Désactivation temporaire de la vérification SSL...")
        # Désactiver temporairement la vérification SSL (non recommandé en production)
        ssl._create_default_https_context = ssl._create_unverified_context
    
    print("🔄 Configuration SSL terminée.")

def main():
    """Fonction principale du script"""
    parser = argparse.ArgumentParser(description="Transcription de fichiers audio de longue durée")
    parser.add_argument("audio_file", help="Chemin vers le fichier audio à transcrire")
    parser.add_argument("-l", "--language", default="fr", help="Code de langue (par défaut: fr)")
    parser.add_argument("-o", "--output", help="Fichier de sortie pour la transcription")
    parser.add_argument("-c", "--chunk", type=int, help="Durée des segments en minutes")
    parser.add_argument("-m", "--model", choices=["tiny", "base", "small", "medium", "large"], 
                        help="Modèle Whisper à utiliser (si mode local)")
    parser.add_argument("-s", "--service", choices=["local", "assemblyai", "openai"], 
                        help="Service de transcription à utiliser")
    parser.add_argument("--no-ssl-fix", action="store_true", 
                        help="Désactiver la correction automatique des certificats SSL")
    
    args = parser.parse_args()
    
    # Mettre à jour la configuration en fonction des arguments
    if args.chunk:
        CONFIG["chunk_duration"] = args.chunk
    
    if args.model:
        CONFIG["whisper_model"] = args.model
    
    if args.service:
        CONFIG["api_service"] = args.service
    
    # Résoudre les problèmes de certificats SSL sur macOS (sauf si --no-ssl-fix est utilisé)
    if not args.no_ssl_fix:
        fix_ssl_certificates_macos()
    
    # Vérifier les dépendances
    if not check_dependencies():
        print("❌ Veuillez installer les dépendances manquantes avant d'exécuter le script.")
        return 1
    
    try:
        # Traiter le fichier
        process_file(args.audio_file, args.language, args.output)
        return 0
    except Exception as e:
        print(f"❌ Erreur: {str(e)}")
        return 1

if __name__ == "__main__":
    print("🎙️ Outil de transcription pour audio longue durée")
    exit(main())

# Outil de Transcription Audio Longue Durée

Cet outil permet de transcrire des fichiers audio de très longue durée (plusieurs heures) en texte. Il est spécialement optimisé pour fonctionner avec macOS, y compris sur les Mac avec puces Apple Silicon (M1/M2/M3).

## Caractéristiques

- ✅ Gestion des fichiers audio très longs (10+ heures)
- ✅ Découpage automatique en segments pour optimiser la mémoire
- ✅ Sauvegarde progressive des résultats
- ✅ Multiple options de transcription (locale ou API)
- ✅ Compatible avec macOS Apple Silicon
- ✅ Correction automatique des problèmes de certificats SSL

## Installation

### Prérequis

- Python 3.7 ou supérieur
- FFmpeg
- Connexion Internet (sauf pour le mode local après installation)

### Étapes d'installation

1. **Installer FFmpeg**

   Sur macOS avec Homebrew :
   ```bash
   brew install ffmpeg
   ```
   
   Sur Ubuntu/Debian :
   ```bash
   sudo apt install ffmpeg
   ```

2. **Installer les dépendances Python**

   Pour une transcription locale (recommandé pour des fichiers longs) :
   ```bash
   pip install -U openai-whisper torch
   ```
   
   Pour utiliser les API externes :
   ```bash
   pip install requests
   ```

3. **Correction des problèmes SSL (macOS uniquement)**

   Si vous rencontrez des erreurs SSL, exécutez :
   ```bash
   python ssl-fix-macos.py
   ```
   
   Ou la commande intégrée à macOS :
   ```bash
   /Applications/Python*/Install\ Certificates.command
   ```

## Utilisation

### Commande de base

```bash
python long-audio-transcription.py chemin/vers/votre_fichier_audio.mp3
```

### Options disponibles

```
Options:
  -h, --help            Afficher l'aide
  -l, --language LANGUAGE
                        Code de langue (par défaut: fr)
  -o, --output OUTPUT   Fichier de sortie pour la transcription
  -c, --chunk CHUNK     Durée des segments en minutes
  -m, --model {tiny,base,small,medium,large}
                        Modèle Whisper à utiliser (mode local)
  -s, --service {local,assemblyai,openai}
                        Service de transcription à utiliser
  --no-ssl-fix          Désactiver la correction automatique des certificats SSL
```

### Exemples d'utilisation

1. **Transcription standard en français** :
   ```bash
   python long-audio-transcription.py mon_audio.mp3
   ```

2. **Transcription en anglais** :
   ```bash
   python long-audio-transcription.py mon_audio.mp3 -l en
   ```

3. **Utiliser un modèle plus précis** (mais plus lent) :
   ```bash
   python long-audio-transcription.py mon_audio.mp3 -m medium
   ```

4. **Spécifier le fichier de sortie** :
   ```bash
   python long-audio-transcription.py mon_audio.mp3 -o ma_transcription.txt
   ```

5. **Ajuster la taille des segments** (en minutes) :
   ```bash
   python long-audio-transcription.py mon_audio.mp3 -c 15
   ```

6. **Utiliser une API externe** (nécessite une clé API configurée dans le script) :
   ```bash
   python long-audio-transcription.py mon_audio.mp3 -s assemblyai
   ```

## Configuration pour API externe

Si vous souhaitez utiliser une API externe (plus rapide mais nécessite un compte), modifiez les clés API dans le script :

```python
# Configuration des API (à remplacer par vos propres clés)
API_KEYS = {
    "assemblyai": "VOTRE_CLE_API_ASSEMBLY_AI",
    "openai": "VOTRE_CLE_API_OPENAI"
}
```

## Recommandations selon la durée du fichier

| Durée de l'audio | Modèle recommandé | Taille des segments | Commentaire |
|------------------|-------------------|---------------------|-------------|
| < 2 heures       | small ou medium   | 10 minutes          | Bonne précision, vitesse raisonnable |
| 2-8 heures       | base ou small     | 10-15 minutes       | Bon équilibre |
| > 8 heures       | tiny ou base      | 15-20 minutes       | Pour les très longs fichiers |

## Résolution de problèmes

### Erreur de certificat SSL

Si vous obtenez une erreur `CERTIFICATE_VERIFY_FAILED`, le script essaiera de la corriger automatiquement. Si l'erreur persiste :

1. Exécutez le script de correction SSL :
   ```bash
   python ssl-fix-macos.py
   ```

2. Ou désactivez temporairement la vérification SSL :
   ```bash
   export PYTHONHTTPSVERIFY=0
   ```

### Problèmes de mémoire

Si vous rencontrez des problèmes de mémoire, réduisez la taille des segments et utilisez un modèle plus petit :
```bash
python long-audio-transcription.py mon_audio.mp3 -c 5 -m tiny
```

### Erreurs FFmpeg

Si FFmpeg signale des erreurs avec votre fichier audio, essayez de le convertir en WAV ou MP3 standard :
```bash
ffmpeg -i mon_audio_problematique.m4a -ar 16000 -ac 1 mon_audio_converti.mp3
```

## Structure des fichiers générés

- `transcription_[nom_fichier]_[timestamp].txt` : Fichier principal contenant la transcription
- `transcription_[nom_fichier]_[timestamp]_log.txt` : Journal détaillé du processus
- `temp_audio/` : Dossier temporaire pour les segments (supprimé automatiquement après traitement)

## Limitations

- La précision de la transcription dépend de la qualité audio et du modèle utilisé
- Les modèles plus précis (medium, large) sont plus lents et consomment plus de RAM
- La transcription locale d'un fichier de 13 heures peut prendre plusieurs heures selon votre matériel

## Licence

Ce script est fourni tel quel, sans garantie d'aucune sorte.

---

*Documentation créée le 7 avril 2025*

# Installer portaudio via Homebrew
brew install portaudio

# Définir les variables d'environnement pour l'installation
export LDFLAGS="-L/opt/homebrew/lib"
export CPPFLAGS="-I/opt/homebrew/include"

# Installer PyAudio avec pip
pip install pyaudio

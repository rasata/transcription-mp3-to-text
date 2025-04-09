#!/usr/bin/env python3
"""
Script pour résoudre les problèmes de certificats SSL sur macOS
Exécutez ce script si vous rencontrez l'erreur:
CERTIFICATE_VERIFY_FAILED] certificate verify failed
"""

import os
import sys
import subprocess
import ssl
import platform

def main():
    """Fonction principale"""
    if platform.system() != "Darwin":
        print("Ce script est uniquement destiné à macOS.")
        return
    
    print("Correction des certificats SSL pour Python sur macOS...")
    
    # Méthode 1: Utiliser le script Install Certificates.command fourni avec Python
    python_dir = sys.exec_prefix
    cert_script = os.path.join(python_dir, "Install Certificates.command")
    
    if os.path.exists(cert_script):
        print(f"Exécution du script: {cert_script}")
        try:
            subprocess.run(["/bin/bash", cert_script], check=True)
            print("Installation des certificats réussie!")
        except subprocess.SubprocessError as e:
            print(f"Erreur lors de l'exécution du script: {e}")
            print("Essai de la méthode alternative...")
            use_alternative_method()
    else:
        print(f"Script d'installation des certificats introuvable: {cert_script}")
        print("Utilisation de la méthode alternative...")
        use_alternative_method()
    
    # Tester si la correction a fonctionné
    test_ssl_connection()

def use_alternative_method():
    """Méthode alternative pour installer les certificats"""
    print("\nMéthode alternative pour installer les certificats:")
    
    try:
        # Méthode 2: Installer les certificats via pip
        print("Installation de certifi...")
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "certifi"], check=True)
        
        # Méthode 3: Créer un contexte SSL non vérifié (temporaire)
        print("\nCréation d'un contexte SSL non vérifié (solution temporaire):")
        print("ATTENTION: Cette méthode désactive la vérification SSL, ce qui n'est pas recommandé")
        print("pour un usage à long terme.")
        
        print("\nAjoutez ce code au début de votre script pour désactiver temporairement la vérification SSL:")
        print("import ssl")
        print("ssl._create_default_https_context = ssl._create_unverified_context")
        
    except Exception as e:
        print(f"Erreur lors de l'installation des certificats: {e}")

def test_ssl_connection():
    """Teste la connexion SSL pour vérifier si la correction a fonctionné"""
    print("\nTest de la connexion SSL...")
    
    try:
        import urllib.request
        urllib.request.urlopen("https://www.google.com")
        print("✅ La connexion SSL fonctionne correctement!")
    except Exception as e:
        print(f"❌ La connexion SSL échoue toujours: {e}")
        print("\nSolution alternative pour votre script:")
        print("1. Ajoutez ces lignes au début de votre script:")
        print("   import ssl")
        print("   ssl._create_default_https_context = ssl._create_unverified_context")
        print("\n2. Ou exécutez cette commande dans votre terminal:")
        print("   /Applications/Python*/Install\\ Certificates.command")

if __name__ == "__main__":
    main()

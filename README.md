# 🎓 BBC School Algeria - Plateforme d'Inscription IA

Système de gestion des inscriptions pour les formations Intelligence Artificielle destinées aux enseignants algériens.

## ✨ Fonctionnalités

- ✅ **Formulaire d'inscription complet** avec validation en temps réel
- 📧 **Emails automatiques** envoyés à `bbcschoolformations@gmail.com` pour chaque inscription
- 🤖 **Chatbot IA intégré** pour répondre aux questions des visiteurs
- 📊 **Dashboard admin** avec statistiques et export CSV
- 🎨 **Interface moderne** responsive et optimisée mobile
- 🔒 **Protection anti-spam** avec rate limiting

## 📋 Prérequis

- Python 3.8+
- Compte Gmail avec authentification à 2 facteurs activée

## 🚀 Installation rapide

### 1. Cloner le projet
```bash
git clone https://github.com/VOTRE_USERNAME/bbc-school.git
cd bbc-school
```

### 2. Installer les dépendances
```bash
pip install -r requirements.txt
```

### 3. Configuration des emails

**Créez un fichier `.env` à la racine du projet** :
```bash
cp .env.example .env
```

**Configurez vos identifiants Gmail dans `.env`** :
```env
EMAIL_ADDRESS=bbcschoolformations@gmail.com
EMAIL_PASSWORD=votre_mot_de_passe_app
```

### 🔐 Comment obtenir un mot de passe d'application Gmail ?

1. Allez sur https://myaccount.google.com/security
2. Activez la **"Validation en deux étapes"**
3. Retournez sur https://myaccount.google.com/apppasswords
4. Sélectionnez **"Application : Autre"** → Nommez-la "BBC School"
5. Copiez le mot de passe généré (16 caractères)
6. Collez-le dans `.env` comme valeur de `EMAIL_PASSWORD`

### 4. Lancer l'application
```bash
python app.py
```

L'application sera accessible sur **http://localhost:5000**

## 📧 Comment récupérer les inscriptions ?

### Méthode 1 : Par email (recommandé)
Chaque nouvelle inscription envoie **automatiquement** un email détaillé à `bbcschoolformations@gmail.com` contenant :
- Nom, prénom, email, téléphone
- Établissement
- Matière enseignée
- Niveau de formation choisi
- Format (présentiel/hybride/en ligne)
- ID unique d'inscription
- Date et heure

### Méthode 2 : Export CSV
Accédez à **http://localhost:5000/export** pour télécharger un fichier CSV avec toutes les inscriptions.

### Méthode 3 : Dashboard JSON
Accédez à **http://localhost:5000/admin** pour voir les statistiques en temps réel (format JSON).

### Méthode 4 : Fichier local
Les données sont sauvegardées dans `data/inscriptions.csv` que vous pouvez ouvrir avec Excel.

## 🌐 Déploiement sur GitHub

### Créer le dépôt GitHub

1. Allez sur https://github.com/new
2. Nommez le dépôt : `bbc-school`
3. Description : `BBC School Algeria - Plateforme de formation IA pour enseignants`
4. Choisissez **Public**
5. **Ne cochez rien** (pas de README, .gitignore, ou licence)
6. Cliquez sur **"Create repository"**

### Pousser votre code

Copiez et collez ces commandes dans votre terminal :

```bash
git remote add origin https://github.com/VOTRE_USERNAME/bbc-school.git
git branch -M master
git push -u origin master
```

Remplacez `VOTRE_USERNAME` par votre nom d'utilisateur GitHub.

## 📁 Structure du projet

```
bbc-school/
├── app.py                  # Application Flask principale
├── requirements.txt        # Dépendances Python
├── .env.example           # Template de configuration
├── .gitignore             # Fichiers à ignorer par Git
├── render.yaml            # Configuration Render.com (optionnel)
├── data/
│   └── inscriptions.csv   # Base de données des inscriptions
├── logs/
│   └── app.log           # Logs de l'application
├── static/
│   ├── logo-BBC-School.jpg
│   └── imag-back-bbc-school.jpg
└── templates/
    └── index.html         # Page d'accueil avec formulaire
```

## 🛠️ Routes disponibles

| Route | Méthode | Description |
|-------|---------|-------------|
| `/` | GET | Page d'accueil avec formulaire d'inscription |
| `/inscription` | POST | Enregistrer une nouvelle inscription |
| `/chatbot` | POST | API du chatbot IA |
| `/admin` | GET | Statistiques et dashboard (JSON) |
| `/export` | GET | Télécharger le CSV des inscriptions |
| `/health` | GET | Vérifier l'état de l'application |

## 🔧 Configuration avancée

### Variables d'environnement (.env)

```env
SECRET_KEY=votre_cle_secrete_unique
EMAIL_ADDRESS=bbcschoolformations@gmail.com
EMAIL_PASSWORD=votre_mot_de_passe_app_gmail
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
PORT=5000
```

## 🐛 Dépannage

### Les emails ne sont pas envoyés
- Vérifiez que `EMAIL_PASSWORD` est bien configuré dans `.env`
- Assurez-vous d'utiliser un **mot de passe d'application**, pas votre mot de passe Gmail habituel
- Vérifiez que la validation en deux étapes est activée sur votre compte Gmail

### Les images ne s'affichent pas
- Vérifiez que les fichiers existent dans `static/` :
  - `logo-BBC-School.jpg`
  - `imag-back-bbc-school.jpg`
- Les noms doivent contenir des tirets `-`, pas des espaces

### Erreur "port already in use"
Changez le port dans `.env` :
```env
PORT=8000
```

## 📞 Support

Pour toute question sur le code, ouvrez une issue sur GitHub.

## 📄 Licence

© 2025 BBC School Algeria - Tous droits réservés

---

**Développé avec ❤️ pour BBC School Algeria**

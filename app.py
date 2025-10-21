from flask import Flask, render_template, request, jsonify, send_file
import csv
import os
from datetime import datetime
import pandas as pd
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
CORS(app)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'bbc-school-2025')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["2000 per day", "500 per hour"]
)

# Logging avec affichage console
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    filename='logs/app.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s'
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger().addHandler(console)

DATA_DIR = 'data'
INSCRIPTIONS_FILE = os.path.join(DATA_DIR, 'inscriptions.csv')

# Configuration email
SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
EMAIL_ADDRESS = os.environ.get('EMAIL_ADDRESS', 'bbcschoolformations@gmail.com')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD', '')  # À configurer dans .env

def init_csv():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(INSCRIPTIONS_FILE):
        with open(INSCRIPTIONS_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'id', 'timestamp', 'prenom', 'nom', 'email', 
                'telephone', 'etablissement', 'matiere', 'niveau', 
                'format', 'ip_address', 'user_agent', 'status'
            ])
        logging.info("✅ Fichier CSV inscriptions initialisé")

def check_images():
    """Vérifie la présence des images critiques avec debug"""
    images = {
        'logo': 'static/logo-BBC-School.jpg',
        'background': 'static/imag-back-bbc-school.jpg',
        'header_facebook': 'static/header-page-facebook.jpg'
    }
    missing = []
    found = []
    
    for name, path in images.items():
        if os.path.exists(path):
            found.append(f"{name}: {os.path.getsize(path)} bytes")
        else:
            missing.append(name)
            logging.warning(f"❌ Image manquante: {path}")
    
    if missing:
        logging.error(f"🚨 Images manquantes: {', '.join(missing)}")
        logging.info("💡 Solution: Renommez vos fichiers dans /static/ avec les bons noms (tirets au lieu d'espaces)")
        logging.info("💡 Exemple: 'logo BBC School.jpg' → 'logo-BBC-School.jpg'")
    else:
        logging.info(f"🖼️  Toutes les images BBC School trouvées: {', '.join(found)}")
    
    return len(missing) == 0

@app.route('/')
def index():
    init_csv()
    images_ok = check_images()
    if not images_ok:
        print("\n🚨 ATTENTION: Certaines images sont manquantes dans /static/")
        print("💡 Vérifiez les noms de fichiers (utilisez des tirets '-', pas d'espaces)")
        print("💡 Ou le template utilisera des fallbacks automatiques\n")
    return render_template('index.html')

@app.route('/test-image')
def test_image():
    return render_template('test-image.html')

@app.route('/inscription', methods=['POST'])
@limiter.limit("10 per hour")
def inscription():
    try:
        # Récupération et nettoyage des données
        data = {
            'id': datetime.now().strftime('%Y%m%d%H%M%S%f')[:14],
            'timestamp': datetime.now().isoformat(),
            'prenom': request.form.get('prenom', '').strip().title(),
            'nom': request.form.get('nom', '').strip().upper(),
            'email': request.form.get('email', '').strip().lower(),
            'telephone': request.form.get('telephone', '').strip(),
            'etablissement': request.form.get('etablissement', '').strip().title(),
            'matiere': request.form.get('matiere', '').strip(),
            'niveau': request.form.get('niveau', ''),
            'format': request.form.get('format', 'presentiel'),
            'ip_address': request.remote_addr or 'unknown',
            'user_agent': request.headers.get('User-Agent', 'unknown')[:200],
            'status': 'confirmé'
        }
        
        # Validation des champs obligatoires
        required_fields = ['prenom', 'nom', 'email', 'etablissement', 'matiere', 'niveau']
        missing = [field for field in required_fields if not data.get(field)]
        if missing:
            error_msg = f"Champs obligatoires manquants : {', '.join([f'{f.title()}' for f in missing])}"
            logging.warning(f"❌ Inscription incomplète: {error_msg}")
            return jsonify({'success': False, 'error': error_msg}), 400
        
        # Validation format email simple
        if '@' not in data['email'] or '.' not in data['email']:
            logging.warning(f"❌ Email invalide: {data['email']}")
            return jsonify({'success': False, 'error': 'Format d\'email invalide'}), 400
        
        # Vérification doublon email
        if check_duplicate_email(data['email']):
            logging.warning(f"❌ Doublon email: {data['email']}")
            return jsonify({'success': False, 'error': 'Cette adresse email est déjà inscrite'}), 400
        
        # Sauvegarde dans CSV
        save_inscription(data)

        # Envoi email de notification à BBC School
        email_sent = send_notification_email(data)

        # Log détaillé
        full_name = f"{data['prenom']} {data['nom']}"
        logging.info(f"✅ INSCRIPTION #{data['id']}: {full_name} ({data['email']})")
        logging.info(f"   📚 Établissement: {data['etablissement']} | Niveau: {data['niveau']} | Matière: {data['matiere']}")
        if email_sent:
            logging.info(f"   📧 Email de notification envoyé à {EMAIL_ADDRESS}")
        else:
            logging.warning(f"   ⚠️ Email non envoyé (configurez EMAIL_PASSWORD dans .env)")

        return jsonify({
            'success': True,
            'message': f"Votre inscription a bien été enregistrée ! ID de confirmation: {data['id']}. Nous vous contacterons bientôt à {data['email']}.",
            'id': data['id'],
            'email': data['email'],
            'full_name': f"{data['prenom']} {data['nom']}"
        }), 200
        
    except Exception as e:
        error_msg = str(e)
        logging.error(f"❌ ERREUR INSCRIPTION: {error_msg}")
        logging.error(f"   Données reçues: {dict(request.form) if request.form else 'Aucune'}")
        return jsonify({
            'success': False,
            'error': 'Erreur technique lors de l\'inscription. Veuillez réessayer dans quelques instants.',
            'debug': error_msg if app.debug else None  # Debug seulement en mode dev
        }), 500

def check_duplicate_email(email):
    """Vérifie si l'email existe déjà dans le CSV"""
    try:
        if not os.path.exists(INSCRIPTIONS_FILE):
            return False
        df = pd.read_csv(INSCRIPTIONS_FILE, encoding='utf-8')
        if len(df) == 0 or 'email' not in df.columns:
            return False
        # Recherche insensible à la casse
        return email.lower() in df['email'].astype(str).str.lower().values
    except Exception as e:
        logging.warning(f"⚠️ Erreur vérification doublon email '{email}': {e}")
        return False

def save_inscription(data):
    """Sauvegarde l'inscription dans le CSV avec gestion d'erreurs"""
    fieldnames = list(data.keys())
    file_exists = os.path.exists(INSCRIPTIONS_FILE)

    try:
        with open(INSCRIPTIONS_FILE, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
                logging.info("📄 Nouveau fichier CSV inscriptions créé")
            writer.writerow(data)
        logging.info(f"💾 Inscription sauvegardée avec succès: {data['id']}")
    except Exception as e:
        logging.error(f"❌ Erreur sauvegarde inscription {data.get('id', 'unknown')}: {e}")
        raise e

def send_notification_email(data):
    """Envoie un email de notification à BBC School pour chaque inscription"""
    try:
        if not EMAIL_PASSWORD:
            logging.warning("⚠️ EMAIL_PASSWORD non configuré - email non envoyé")
            return False

        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"✅ Nouvelle inscription BBC School - {data['prenom']} {data['nom']}"
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = EMAIL_ADDRESS

        # Corps de l'email en HTML
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white; border-radius: 10px; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                <h2 style="color: #4267B2; border-bottom: 3px solid #FF6B35; padding-bottom: 10px;">
                    📝 Nouvelle inscription BBC School
                </h2>

                <div style="margin: 20px 0;">
                    <h3 style="color: #333;">👤 Informations du candidat</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 8px; background-color: #f8f9fa; font-weight: bold; width: 40%;">Nom complet:</td>
                            <td style="padding: 8px;">{data['prenom']} {data['nom']}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; background-color: #f8f9fa; font-weight: bold;">Email:</td>
                            <td style="padding: 8px;"><a href="mailto:{data['email']}">{data['email']}</a></td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; background-color: #f8f9fa; font-weight: bold;">Téléphone:</td>
                            <td style="padding: 8px;">{data.get('telephone', 'Non renseigné')}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; background-color: #f8f9fa; font-weight: bold;">Établissement:</td>
                            <td style="padding: 8px;">{data['etablissement']}</td>
                        </tr>
                    </table>
                </div>

                <div style="margin: 20px 0;">
                    <h3 style="color: #333;">📚 Détails de la formation</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 8px; background-color: #f8f9fa; font-weight: bold; width: 40%;">Matière:</td>
                            <td style="padding: 8px;">{data['matiere']}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; background-color: #f8f9fa; font-weight: bold;">Niveau:</td>
                            <td style="padding: 8px;">{data['niveau'].upper()}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; background-color: #f8f9fa; font-weight: bold;">Format:</td>
                            <td style="padding: 8px;">{data['format']}</td>
                        </tr>
                    </table>
                </div>

                <div style="margin: 20px 0; padding: 15px; background-color: #e3f2fd; border-left: 4px solid #4267B2; border-radius: 5px;">
                    <p style="margin: 5px 0;"><strong>ID inscription:</strong> {data['id']}</p>
                    <p style="margin: 5px 0;"><strong>Date:</strong> {data['timestamp']}</p>
                    <p style="margin: 5px 0;"><strong>IP:</strong> {data['ip_address']}</p>
                </div>

                <div style="margin-top: 30px; padding-top: 20px; border-top: 2px solid #e0e0e0; text-align: center; color: #666;">
                    <p>BBC School Algeria - Système d'inscription automatique</p>
                    <p style="font-size: 12px;">Cet email a été généré automatiquement</p>
                </div>
            </div>
        </body>
        </html>
        """

        msg.attach(MIMEText(html_body, 'html'))

        # Envoi de l'email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)

        logging.info(f"📧 Email de notification envoyé à {EMAIL_ADDRESS} pour {data['email']}")
        return True

    except Exception as e:
        logging.error(f"❌ Erreur envoi email: {e}")
        return False

@app.route('/chatbot', methods=['POST'])
def chatbot():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'reply': "Désolé, je n'ai pas compris votre message."}), 400
        
        question = data.get('msg', '').lower().strip()
        if not question:
            return jsonify({'reply': "Posez-moi une question sur BBC School !"}), 400
        
        # Base de connaissances BBC School étendue
        faq_responses = {
            'bonjour': "Bonjour ! Bienvenue chez BBC School Algeria. Je suis votre assistant IA pour la formation Intelligence Artificielle adaptée aux enseignants. Comment puis-je vous aider aujourd'hui ?",
            'formation': "BBC School propose une formation certifiante en IA spécifiquement conçue pour les enseignants algériens. Programme de 6 semaines avec certification officielle reconnue.",
            'tarif': "Nos tarifs sont compétitifs : Formation Débutant 45.000 DZD | Intermédiaire 55.000 DZD | Avancé 65.000 DZD. Possibilités de paiement échelonné sur 3 mois sans frais.",
            'horaire': "Les sessions BBC School se déroulent du lundi au vendredi, de 09h00 à 17h00 avec pause déjeuner de 12h30 à 14h00. Format hybride disponible (présentiel + en ligne).",
            'inscription': "L'inscription se fait directement via le formulaire en ligne. Vous recevrez immédiatement un email de confirmation avec votre ID unique et le programme détaillé de la formation.",
            'contact': "Contactez-nous facilement : 📧 contact@bbcschool.dz | 📞 +213 661 12 34 56 | 📍 Centre-ville d'Alger, près de la poste centrale (heures d'ouverture 8h-18h).",
            'durée': "Durée complète : 6 semaines intensives (120 heures totales - 24 sessions de 5 heures). Certification BBC School Algeria incluse et reconnue par l'éducation nationale.",
            'certificat': "Absolument ! Toutes nos formations délivrents un certificat officiel BBC School Algeria, valable pour vos promotions, avancements de carrière et heures de formation continue.",
            'en ligne': "Nous proposons un format hybride optimal : 60% présentiel à Alger pour les travaux pratiques, 40% en ligne via notre plateforme sécurisée Zoom + Moodle pour plus de flexibilité.",
            'prérequis': "Aucun prérequis technique requis ! Il suffit d'avoir un ordinateur moderne (Windows 10+, Mac OS, ou Linux), 8 Go de RAM minimum, et une connexion internet stable (4G ou fibre).",
            'contenu': "Programme complet : Introduction à Python pour l'IA, Machine Learning pratique, Création de chatbots éducatifs, Traitement automatique du langage (NLP), Outils IA pour l'enseignement, Éthique et réglementation IA.",
            'financement': "Plusieurs options : paiement comptant, paiement en 3 fois sans frais, financement via les établissements scolaires, ou bourses partielles pour les enseignants prioritaires."
        }
        
        # Recherche intelligente de mots-clés
        question_words = question.split()
        best_match = None
        best_score = 0
        
        for keyword, response in faq_responses.items():
            keyword_words = keyword.split()
            matches = sum(1 for word in keyword_words if word in question_words)
            score = matches / len(keyword_words) if keyword_words else 0
            if score > best_score:
                best_score = score
                best_match = response
        
        # Si bonne correspondance
        if best_score > 0.3:  # Seuil de pertinence
            logging.info(f"🤖 Chatbot: Réponse FAQ pour '{keyword}'")
            return jsonify({'reply': best_match})
        
        # Réponses contextuelles avancées
        if any(word in question for word in ['prix', 'coût', 'budget', 'financement', 'tarif']):
            return jsonify({
                'reply': "Les formations BBC School IA sont très accessibles financièrement :\n\n💰 **Tarifs** :\n• Débutant : 45.000 DZD\n• Intermédiaire : 55.000 DZD\n• Avancé : 65.000 DZD\n\n💳 **Options de paiement** :\n• Paiement comptant (remise 5%)\n• 3 × sans frais\n• Financement établissement\n• Bourses enseignants prioritaires\n\nContactez-nous pour un devis personnalisé ! 📧 contact@bbcschool.dz"
            })
        
        if any(word in question for word in ['email', 'confirmation', 'reçu', 'mail']):
            return jsonify({
                'reply': "Votre email de confirmation BBC School contient :\n\n📋 **ID unique** de votre inscription\n📅 Programme détaillé et dates de session\n💰 Modalités de paiement et facturation\n📍 Adresse et horaires des cours\n📧 Coordonnées complètes du support\n\nL'email arrive normalement dans les 5 minutes. Vérifiez votre dossier spam si nécessaire."
            })
        
        # Réponse par défaut intelligente avec variation
        default_replies = [
            "Je suis l'assistant IA officiel de BBC School Algeria, spécialisé dans la formation certifiante Intelligence Artificielle pour enseignants. Posez-moi des questions précises sur :\n\n• Le programme de formation\n• Les tarifs et financements\n• Les modalités d'inscription\n• Les horaires et durée\n• Le certificat délivré\n• Les prérequis techniques\n\nOu contactez-nous directement au +213 661 12 34 56 !",
            "BBC School est leader en formation IA éducative en Algérie. Notre programme de 6 semaines vous formera à utiliser l'IA dans vos cours : chatbots, analyse de données élèves, correction automatique, et outils pédagogiques innovants. Certification officielle incluse !",
            "Pour toute question spécifique sur votre inscription ou la formation, vous pouvez aussi nous joindre :\n\n📧 contact@bbcschool.dz\n📞 +213 661 12 34 56\n🕒 Lundi-Vendredi 8h-18h\n📍 Centre-ville d'Alger"
        ]
        import random
        reply = random.choice(default_replies)
        logging.info(f"🤖 Chatbot: Réponse par défaut pour '{question[:50]}...'")
        return jsonify({'reply': reply})
        
    except Exception as e:
        logging.error(f"❌ Erreur chatbot: {e}")
        return jsonify({
            'reply': "Désolé, l'assistant IA rencontre un problème temporaire. Vous pouvez nous contacter directement :\n\n📧 contact@bbcschool.dz\n📞 +213 661 12 34 56\n\nNous répondrons dans l'heure !"
        })

@app.route('/admin')
def admin():
    try:
        init_csv()
        if not os.path.exists(INSCRIPTIONS_FILE) or os.path.getsize(INSCRIPTIONS_FILE) == 0:
            return jsonify({
                'total': 0, 
                'message': 'Aucune inscription enregistrée pour le moment',
                'status': 'empty'
            })
        
        df = pd.read_csv(INSCRIPTIONS_FILE, encoding='utf-8')
        if len(df) == 0:
            return jsonify({'total': 0, 'message': 'Aucune inscription'})
        
        today = datetime.now().strftime('%Y-%m-%d')
        stats = {
            'total': len(df),
            'aujourd_hui': len(df[df['timestamp'].str.contains(today, na=False)]),
            'derniere_inscription': df.iloc[-1].get('timestamp', 'N/A'),
            'par_niveau': df['niveau'].value_counts().to_dict() if 'niveau' in df.columns else {},
            'par_format': df['format'].value_counts().to_dict() if 'format' in df.columns else {},
            'derniers_inscrits': df.tail(5)[['prenom', 'nom', 'email', 'timestamp']].to_dict('records'),
            'export_url': f'/export',
            'csv_path': INSCRIPTIONS_FILE
        }
        logging.info(f"📊 Admin stats: {stats['total']} inscriptions totales")
        return jsonify(stats)
    except Exception as e:
        logging.error(f"❌ Erreur admin: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/export')
def export():
    try:
        init_csv()
        if not os.path.exists(INSCRIPTIONS_FILE) or os.path.getsize(INSCRIPTIONS_FILE) == 0:
            return jsonify({'error': 'Aucune donnée à exporter pour le moment'}), 404
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        filename = f"bbc_school_inscriptions_{timestamp}.csv"
        logging.info(f"📤 Export CSV demandé: {filename}")
        return send_file(
            INSCRIPTIONS_FILE, 
            as_attachment=True, 
            download_name=filename,
            mimetype='text/csv'
        )
    except Exception as e:
        logging.error(f"❌ Erreur export: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health():
    try:
        init_csv()
        images_ok = check_images()
        df = pd.read_csv(INSCRIPTIONS_FILE) if os.path.exists(INSCRIPTIONS_FILE) else pd.DataFrame()
        return jsonify({
            'status': 'healthy', 
            'timestamp': datetime.now().isoformat(),
            'images_ok': images_ok,
            'csv_exists': os.path.exists(INSCRIPTIONS_FILE),
            'inscriptions_count': len(df),
            'debug_images': check_images()  # Force check pour debug
        })
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

if __name__ == '__main__':
    print("=" * 70)
    print("BBC SCHOOL ALGERIA - SERVEUR FLASK PROFESSIONNEL")
    print("=" * 70)
    print("Initialisation de l'environnement...")
    
    # Création des dossiers nécessaires
    for dir_path in ['data', 'logs', 'static', 'templates']:
        os.makedirs(dir_path, exist_ok=True)
        print(f"Creation dossier: {dir_path}/ OK")
    
    # Initialisation base de données CSV
    init_csv()
    
    # Vérification des images avec debug détaillé
    print("\nVerification des images BBC School...")
    images_ok = check_images()
    if images_ok:
        print("OK - Toutes les images sont correctement configurees")
    else:
        print("ATTENTION: Certaines images sont manquantes ou mal nommees")
        print("SOLUTION RAPIDE: Renommez vos fichiers dans /static/")
        print("   Exemple 1: 'logo BBC School.jpg' -> 'logo-BBC-School.jpg'")
        print("   Exemple 2: 'imag back bbc school.jpg' -> 'imag-back-bbc-school.jpg'")
        print("   Exemple 3: Ajoutez 'header-page-facebook.jpg' pour le bandeau")
        print("\nLe site utilisera des images de fallback automatiques")

    print("\nSERVEUR PRET ET OPERATIONNEL !")
    print("Page d'accueil: http://localhost:5000")
    print("Dashboard admin: http://localhost:5000/admin (JSON)")
    print("Export CSV: http://localhost:5000/export")
    print("Health check: http://localhost:5000/health")
    print("Chatbot API: POST /chatbot")
    print("=" * 70)
    
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)

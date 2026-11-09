"""
documents.py
Génération du CV (Excel), de la lettre de motivation, et envoi d'un
email de confirmation de candidature.

MODE TEST : l'email de confirmation est envoyé à l'adresse personnelle
de l'étudiant (celle de son propre profil), jamais à l'entreprise. Le
message indique explicitement qu'il s'agit d'un test et ne prétend
jamais que l'entreprise a réellement reçu la candidature.

Utilise uniquement les informations réellement présentes dans le profil
(SQLite) et dans l'entreprise choisie. Aucune donnée n'est inventée.
"""

import mimetypes
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path

from dotenv import load_dotenv
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from src.utils.paths import chemin_configuration, chemin_donnees

DOSSIER_SORTIE = chemin_donnees("reports", "documents_candidat")
load_dotenv(chemin_configuration(), override=False)

VIDE = "-"
BLEU_HEX = "2563EB"
MARINE_HEX = "0F1B4C"


def texte(valeur):
    if valeur is None or str(valeur).strip() in ("", "nan"):
        return VIDE
    return str(valeur)


# ---------- CV (Excel, openpyxl) ----------
def generer_cv_excel(profil):
    """Crée un CV Excel à partir du profil SQLite. Retourne le chemin du fichier créé."""
    DOSSIER_SORTIE.mkdir(parents=True, exist_ok=True)
    classeur = Workbook()
    feuille = classeur.active
    feuille.title = "CV"
    feuille.column_dimensions["A"].width = 22
    feuille.column_dimensions["B"].width = 60

    police_titre = Font(size=18, bold=True, color=MARINE_HEX)
    police_section = Font(size=12, bold=True, color="FFFFFF")
    fond_section = PatternFill("solid", fgColor=BLEU_HEX)
    police_normale = Font(size=11)

    nom_complet = f"{texte(profil.get('prenom'))} {texte(profil.get('nom'))}".strip()
    feuille["A1"] = nom_complet
    feuille["A1"].font = police_titre
    feuille.merge_cells("A1:B1")

    contact = (f"{texte(profil.get('email'))}  ·  {texte(profil.get('telephone'))}  ·  "
              f"{texte(profil.get('ville'))}")
    feuille["A2"] = contact
    feuille.merge_cells("A2:B2")

    ligne = 4

    def section(titre_section):
        nonlocal ligne
        feuille.cell(row=ligne, column=1, value=titre_section).font = police_section
        feuille.cell(row=ligne, column=1).fill = fond_section
        feuille.cell(row=ligne, column=2).fill = fond_section
        feuille.merge_cells(start_row=ligne, start_column=1, end_row=ligne, end_column=2)
        ligne += 1

    def champ(titre_champ, valeur):
        nonlocal ligne
        feuille.cell(row=ligne, column=1, value=titre_champ).font = Font(bold=True, size=11)
        cellule = feuille.cell(row=ligne, column=2, value=texte(valeur))
        cellule.font = police_normale
        cellule.alignment = Alignment(wrap_text=True, vertical="top")
        ligne += 1

    section("Formation")
    champ("Diplôme préparé", profil.get("diplome"))
    champ("Secteur étudié", profil.get("secteur"))
    champ("Établissement", profil.get("etablissement"))

    ligne += 1
    section("Recherche")
    champ("Je cherche", profil.get("recherche"))

    ligne += 1
    section("Compétences")
    feuille.cell(row=ligne, column=1, value="Compétences").font = Font(bold=True, size=11)
    cellule = feuille.cell(row=ligne, column=2, value=texte(profil.get("competences")))
    cellule.alignment = Alignment(wrap_text=True, vertical="top")
    feuille.row_dimensions[ligne].height = 60
    ligne += 1

    ligne += 1
    section("Liens")
    champ("LinkedIn", profil.get("linkedin"))

    nom_fichier = f"CV_{texte(profil.get('nom')).replace(' ', '_')}.xlsx"
    chemin = DOSSIER_SORTIE / nom_fichier
    classeur.save(chemin)
    return chemin


# ---------- LETTRE DE MOTIVATION ----------

def generer_lettre_motivation(profil, entreprise=None):
    """Génère une lettre à partir du profil, adaptée à l'entreprise si fournie."""

    nom_complet = f"{texte(profil.get('prenom'))} {texte(profil.get('nom'))}".strip()
    recherche = texte(profil.get("recherche")) or "stage"
    diplome = texte(profil.get("diplome")) or "formation en cours"
    etablissement = texte(profil.get("etablissement"))
    competences = texte(profil.get("competences"))

    if entreprise:
        nom_entreprise = texte(entreprise.get("Nom_Entreprise"))
        domaine = texte(entreprise.get("Domaine")).lower()
        intro = (
            f"Je me permets de vous adresser ma candidature pour un poste de "
            f"{recherche} au sein de {nom_entreprise}, dont les activités dans le "
            f"secteur {domaine} correspondent à mon projet professionnel."
        )
    else:
        intro = (
            f"Je me permets de vous adresser ma candidature pour un poste de "
            f"{recherche}, en cohérence avec mon projet professionnel."
        )

    if etablissement:
        formation = f"Actuellement en {diplome} à {etablissement}"
    else:
        formation = f"Actuellement en {diplome}"

    if competences:
        phrase_formation = (
            f"{formation}, j'ai développé des compétences en {competences}."
        )
    else:
        phrase_formation = (
            f"{formation}, je développe progressivement mes compétences professionnelles."
        )

    return (
        f"Objet : Candidature - {recherche}\n\n"
        f"Madame, Monsieur,\n\n"
        f"{intro}\n\n"
        f"{phrase_formation}\n\n"
        f"Je suis convaincu(e) que ce profil pourrait répondre à vos besoins, et je "
        f"me tiens à votre disposition pour un entretien.\n\n"
        f"Je vous remercie de l'attention portée à ma candidature et vous prie "
        f"d'agréer, Madame, Monsieur, l'expression de mes salutations distinguées.\n\n"
        f"{nom_complet}\n"
        f"{texte(profil.get('email'))} - {texte(profil.get('telephone'))}\n"
    )

# ---------- ENVOI DE L'EMAIL DE TEST (destinataire = l'étudiant lui-même) ----------
def envoyer_confirmation_test(profil, entreprise, date_candidature):
    """
    Envoie un email de confirmation de candidature EN MODE TEST :
    - le destinataire est TOUJOURS l'adresse personnelle de l'étudiant,
      jamais l'email de l'entreprise ;
    - le CV réel du profil est joint quand il existe ;
    - le message précise explicitement qu'il s'agit d'un test et ne
      prétend jamais que l'entreprise a réellement reçu la candidature.

    Fonctionne même si l'entreprise n'a pas d'adresse email connue,
    puisque l'entreprise n'est jamais destinataire.

    Retourne (succes: bool, message: str).
    """
    expediteur = os.getenv("SMTP_EMAIL")
    mot_de_passe = os.getenv("SMTP_MOT_DE_PASSE")
    serveur_smtp = os.getenv("SMTP_SERVEUR", "smtp.gmail.com")
    port_smtp = int(os.getenv("SMTP_PORT", "587"))

    destinataire = profil.get("email")
    nom_entreprise = texte(entreprise.get("Nom_Entreprise"))
    poste = texte(profil.get("recherche"))
    domaine = texte(entreprise.get("Domaine"))
    chemin_cv = profil.get("cv_chemin")

    corps = (
        f"Bonjour {texte(profil.get('prenom'))},\n\n"
        f"[MODE TEST] Cet email est envoyé à ta propre adresse "
        f"({texte(destinataire)}) pour simuler et vérifier la confirmation "
        f"de candidature. Il ne s'agit PAS d'un email reçu par l'entreprise :\n\n"
        f"Votre candidature a été envoyée avec succès à {nom_entreprise}.\n\n"
        f"- Entreprise : {nom_entreprise}\n"
        f"- Opportunité / poste recherché : {poste}\n"
        f"- Domaine : {domaine}\n"
        f"- Date d'envoi : {date_candidature}\n\n"
        f"Ton CV est joint à cet email s'il a bien été trouvé dans ton profil.\n\n"
        f"AJI TSTAJI"
    )

    if not expediteur or not mot_de_passe or not destinataire:
        DOSSIER_SORTIE.mkdir(parents=True, exist_ok=True)
        chemin_recu = DOSSIER_SORTIE / f"Test_confirmation_{nom_entreprise.replace(' ', '_')}.txt"
        chemin_recu.write_text(corps, encoding="utf-8")
        return False, (f"Email de test non envoyé (SMTP non configuré dans .env, ou email "
                       f"personnel manquant dans le profil). Un reçu local a été créé : "
                       f"{chemin_recu}")

    message = EmailMessage()
    message["Subject"] = f"[TEST] Candidature envoyée à {nom_entreprise}"
    message["From"] = expediteur
    message["To"] = destinataire
    message.set_content(corps)

    cv_joint = False
    if chemin_cv and Path(chemin_cv).is_file():
        chemin_cv_path = Path(chemin_cv)
        type_mime, _ = mimetypes.guess_type(chemin_cv_path.name)
        type_principal, sous_type = (type_mime.split("/", 1) if type_mime
                                     else ("application", "octet-stream"))
        with open(chemin_cv_path, "rb") as fichier:
            message.add_attachment(fichier.read(), maintype=type_principal,
                                   subtype=sous_type, filename=chemin_cv_path.name)
        cv_joint = True
    else:
        message.set_content(corps + "\n\n(Aucun CV valide n'a été trouvé dans le profil : "
                                    "rien n'a été joint à ce test.)")

    try:
        with smtplib.SMTP(serveur_smtp, port_smtp, timeout=15) as serveur:
            serveur.starttls()
            serveur.login(expediteur, mot_de_passe)
            serveur.send_message(message)
        precision_cv = "avec le CV en pièce jointe" if cv_joint else "sans CV joint (aucun trouvé)"
        return True, (f"Email de TEST envoyé avec succès à {destinataire}, {precision_cv}. "
                      f"Rappel : ceci confirme uniquement l'enregistrement dans l'application "
                      f"— {nom_entreprise} n'a rien reçu réellement.")
    except Exception as erreur:
        DOSSIER_SORTIE.mkdir(parents=True, exist_ok=True)
        chemin_recu = DOSSIER_SORTIE / f"Test_confirmation_{nom_entreprise.replace(' ', '_')}.txt"
        chemin_recu.write_text(corps, encoding="utf-8")
        return False, (f"Échec réel de l'envoi de l'email de test ({erreur}). "
                       f"Un reçu local a été créé : {chemin_recu}")

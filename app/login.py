"""
login_page.py : Page d'authentification AJI TSTAJI (CustomTkinter)

À placer dans le dossier de vos pages/vues (ex. ui/ ou pages/), à côté de
vos pages Entreprises, Analyse et Chatbot AI.

Dépendances : customtkinter, pillow
Assets :
    assets/marrakech.jpg  -> photo de Marrakech (Koutoubia), rognée en cercle
    assets/logo.png       -> logo AJI TSTAJI en COULEUR (bleu, PNG transparent)
                             (le fond étant clair, n'utilisez plus la version blanche)
Si un asset est absent, un dégradé bleu (photo) ou rien (logo) est utilisé.
"""
import os
import re
import tkinter as tk
import tkinter.font as tkfont
import customtkinter as ctk
from PIL import Image, ImageChops, ImageDraw, ImageTk

# ----------------------------------------------------------------------------
# THÈME : remplacez ces valeurs par les constantes de votre application
# ----------------------------------------------------------------------------
COLORS = {
    "primary":        "#1D4ED8",   # bleu principal (boutons, liens)
    "primary_hover":  "#1E40AF",
    "primary_light":  "#EAF1FF",   # fond de survol léger
    "navy":           "#0B1F4D",
    "navy_deep":      "#061233",
    "sky":            "#3B82F6",
    "bg":             "#FFFFFF",   # fond du panneau droit
    "input_bg":       "#F8FAFC",
    "border":         "#D6DEEA",
    "text":           "#0F172A",
    "text_muted":     "#64748B",
    "error":          "#DC2626",
    # --- panneau gauche (nouveau) ---
    "left_bg":        "#EDF4FC",   # fond bleu très clair
    "wave":           "#CFE1F5",   # bande courbe
    "brand":          "#0B3D91",   # bleu foncé du titre et des textes
}
FONT = "Segoe UI"

# Dossier assets = "assets" à côté de CE fichier (indépendant du dossier de lancement)
ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


def _resolve_asset(path, defaults):
    """Trouve l'image : chemin donné, sinon même nom dans assets/ (.png/.jpg/.jpeg),
    sinon les noms par défaut. Retourne None si rien n'existe."""
    cands = []
    if path:
        base = os.path.basename(path)
        stem = os.path.splitext(base)[0]
        cands += [path, os.path.join(ASSETS_DIR, base)]
        cands += [os.path.join(ASSETS_DIR, stem + e) for e in (".png", ".jpg", ".jpeg")]
    cands += [os.path.join(ASSETS_DIR, d) for d in defaults]
    for c in cands:
        if os.path.exists(c):
            return c
    return None


EMAIL_RE = re.compile(r"^[\w.+\-]+@[\w\-]+(\.[\w\-]+)+$")


# ----------------------------------------------------------------------------
# Rendu du panneau gauche
# ----------------------------------------------------------------------------
def _hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _vertical_gradient(w, h, top, bottom):
    mask = Image.linear_gradient("L").resize((w, h))
    return Image.composite(
        Image.new("RGB", (w, h), _hex_to_rgb(bottom)),
        Image.new("RGB", (w, h), _hex_to_rgb(top)),
        mask,
    )


def _layout(w, h):
    """Toutes les positions/tailles dépendent de (w, h) => rien n'est coupé."""
    s = max(0.55, min(w / 500, h / 680))
    d = int(min(0.40 * h, 0.68 * w))            # diamètre de la photo ronde
    circ_top = int(0.34 * h)
    return {
        "s": s,
        "cx": int(w * 0.46),
        "head_y": int(0.12 * h),
        "title_pt": max(16, int(30 * s)),
        "tag_pt": max(9, int(13 * s)),
        "cap_pt": max(8, int(11 * s)),
        "logo_h": int(0.105 * h),
        "tag_y": int(0.265 * h),
        "d": d,
        "circ_top": circ_top,
        "bar_y": circ_top + d + int(0.045 * h),
        "cap_y": circ_top + d + int(0.115 * h),
    }


def _logo_size(path, lh):
    if path and os.path.exists(path):
        im = Image.open(path)
        return int(im.width * lh / im.height), lh
    return 0, 0


def _extract_photo_if_design(img):
    """Si l'image est le design complet (fond clair + titre + photo ronde + légende),
    on n'en garde que la photo ronde de la Koutoubia. Sinon on la laisse telle quelle."""
    w, h = img.size
    corners = [img.getpixel(p) for p in ((2, 2), (w - 3, 2), (2, h - 3), (w // 2, 2))]
    is_design = w / h > 1.2 and sum(1 for c in corners if sum(c) / 3 > 225) >= 3
    if not is_design:
        return img
    cx, cy = int(w * 0.5007), int(h * 0.540)        # centre de la photo ronde
    half = int(h * 0.246)                            # un peu en dessous du rayon : sans anneau
    return img.crop((cx - half, cy - half, cx + half, cy + half))


def _circle_photo(path, size, ring_px, ring_color):
    """Photo rognée en cercle + anneau bleu, lissée par sur-échantillonnage."""
    k = 4
    big = size * k
    ring = ring_px * k
    inner = big - 2 * ring
    if path and os.path.exists(path):
        img = _extract_photo_if_design(Image.open(path).convert("RGB"))
        sq = min(img.size)
        l, t = (img.width - sq) // 2, (img.height - sq) // 2
        img = img.crop((l, t, l + sq, t + sq)).resize((inner, inner), Image.LANCZOS)
    else:
        img = _vertical_gradient(inner, inner, COLORS["sky"], COLORS["navy"])

    mask = Image.new("L", (inner, inner), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, inner - 1, inner - 1), fill=255)
    out = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    ImageDraw.Draw(out).ellipse((0, 0, big - 1, big - 1), fill=_hex_to_rgb(ring_color))
    out.paste(img, (ring, ring), mask)
    return out.resize((size, size), Image.LANCZOS)


def _wave_mask(w, h, right_frac):
    """Forme à bord droit courbe (anti-aliasée en 2x)."""
    W2, H2 = w * 2, h * 2
    m = Image.new("L", (W2, H2), 0)
    d = ImageDraw.Draw(m)
    d.ellipse((-W2 * 0.6, -H2 * 0.12, W2 * right_frac, H2 * 1.12), fill=255)
    d.rectangle((0, 0, int(W2 * 0.2), H2), fill=255)
    return m.resize((w, h), Image.LANCZOS)


def build_hero(w, h, L, image_path, logo_path, logo_xy):
    """Image PIL (w x h) du panneau gauche (sans le texte, dessiné sur le canvas)."""
    base = Image.new("RGB", (w, h), _hex_to_rgb(COLORS["bg"]))
    # bande courbe + fond clair
    base.paste(Image.new("RGB", (w, h), _hex_to_rgb(COLORS["wave"])),
               mask=_wave_mask(w, h, 1.00))
    base.paste(Image.new("RGB", (w, h), _hex_to_rgb(COLORS["left_bg"])),
               mask=_wave_mask(w, h, 0.92))

    # photo ronde
    d = L["d"]
    photo = _circle_photo(image_path, d, max(4, int(8 * L["s"])), COLORS["primary"])
    base.paste(photo, (L["cx"] - d // 2, L["circ_top"]), photo)

    # logo
    lw, lh = _logo_size(logo_path, L["logo_h"])
    if lw:
        logo = Image.open(logo_path).convert("RGBA").resize((lw, lh), Image.LANCZOS)
        base.paste(logo, logo_xy, logo)
    return base


def _feather_mask(nw, nh, fh, fv):
    """Masque opaque au centre, qui s'estompe sur les 4 bords (fondu sans couture)."""
    ramp = Image.linear_gradient("L")                      # 0 (haut) -> 255 (bas)
    v = Image.new("L", (nw, nh), 255)
    top = ramp.resize((nw, fv))
    v.paste(top, (0, 0))
    v.paste(top.transpose(Image.FLIP_TOP_BOTTOM), (0, nh - fv))
    hz = Image.new("L", (nw, nh), 255)
    left = ramp.transpose(Image.ROTATE_90).resize((fh, nh))  # 0 (gauche) -> 255
    hz.paste(left, (0, 0))
    hz.paste(left.transpose(Image.FLIP_LEFT_RIGHT), (nw - fh, 0))
    return ImageChops.multiply(v, hz)


def _fit_full_design(w, h, path):
    """Design complet (logo + titre + photo ronde + légende) placé dans un
    panneau en demi-cercle : bord droit courbe, textes entièrement visibles."""
    img = Image.open(path).convert("RGB")
    iw, ih = img.size
    # zone utile : on retire la marge gauche et la vague décorative de droite
    crop = img.crop((int(iw * 0.03), 0, int(iw * 0.775), ih))
    cw, ch = crop.size
    bg = img.getpixel((int(iw * 0.02), int(ih * 0.40)))     # couleur de fond de l'image

    # taille : le contenu doit tenir DANS la courbe (0.86 de la largeur)
    scale = min(0.86 * w / cw, 0.94 * h / ch)
    nw, nh = max(2, int(cw * scale)), max(2, int(ch * scale))
    crop = crop.resize((nw, nh), Image.LANCZOS)
    fh = max(8, int(50 * scale))      # fondu horizontal (marges vides seulement)
    fv = max(6, int(28 * scale))      # fondu vertical

    # fond blanc -> bande bleue courbe -> forme claire courbe
    out = Image.new("RGB", (w, h), _hex_to_rgb(COLORS["bg"]))
    out.paste(Image.new("RGB", (w, h), _hex_to_rgb(COLORS["wave"])),
              mask=_wave_mask(w, h, 1.00))
    out.paste(Image.new("RGB", (w, h), bg), mask=_wave_mask(w, h, 0.965))

    # contenu centré dans la zone gauche, fondu sur les bords
    x = max(0, int((0.90 * w - nw) / 2))
    y = (h - nh) // 2
    out.paste(crop, (x, y), _feather_mask(nw, nh, fh, fv))
    return out


# ----------------------------------------------------------------------------
# Page de connexion
# ----------------------------------------------------------------------------
class LoginPage(ctk.CTkFrame):
    """
    Page d'authentification.

    Paramètres
    ----------
    master             : conteneur (fenêtre principale ou frame)
    on_login(email, password)
        Votre fonction d'authentification existante. Peut retourner :
          - True / None            -> succès
          - False                  -> échec (message générique)
          - (ok: bool, msg: str)   -> succès/échec avec message
        ou lever une exception (le message est affiché).
    on_success()       : appelé après une connexion réussie (afficher l'app)
    on_register()      : clic sur « Créer un compte »
    on_forgot_password(): clic sur « Mot de passe oublié ? »
    hero_image / logo_image : chemins des assets
    """

    def __init__(self, master, on_login, on_success=None, on_register=None,
                 on_forgot_password=None, hero_image=None,
                 logo_image=None, hero_is_full_design=True, **kwargs):
        super().__init__(master, fg_color=COLORS["bg"], corner_radius=0, **kwargs)
        self._on_login = on_login
        self._on_success = on_success
        self._on_register = on_register
        self._on_forgot = on_forgot_password
        self._hero_image = _resolve_asset(hero_image, ("marrakech.png", "marrakech.jpg", "hero.png"))
        self._logo_image = _resolve_asset(logo_image, ("logo.png",))
        self._full_design = hero_is_full_design
        self._photo = None
        self._resize_job = None
        self._pwd_visible = False

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=11, uniform="cols")
        self.grid_columnconfigure(1, weight=9, uniform="cols")

        self._build_left()
        self._build_right()

    # ------------------------------------------------------------ gauche
    def _build_left(self):
        self.canvas = tk.Canvas(self, bg=COLORS["bg"], highlightthickness=0, bd=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.canvas.bind("<Configure>", self._schedule_redraw)

    def _schedule_redraw(self, event):
        if self._resize_job:
            self.after_cancel(self._resize_job)
        self._resize_job = self.after(
            80, lambda: self._draw_left(event.width, event.height))

    def _draw_left(self, w, h):
        if w < 100 or h < 100:
            return
        if self._full_design and self._hero_image and os.path.exists(self._hero_image):
            self._photo = ImageTk.PhotoImage(_fit_full_design(w, h, self._hero_image))
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, image=self._photo, anchor="nw")
            return
        L = _layout(w, h)
        cx = L["cx"]

        # --- géométrie de l'en-tête : [logo] | AJI TSTAJI, centré sur cx ---
        title_font = tkfont.Font(family=FONT, size=L["title_pt"], weight="bold")
        title_w = title_font.measure("AJI TSTAJI")
        lw, lh = _logo_size(self._logo_image, L["logo_h"])
        gap = int(14 * L["s"])
        total = (lw + gap + 2 + gap if lw else 0) + title_w
        x0 = cx - total // 2
        logo_xy = (x0, L["head_y"] - lh // 2)

        img = build_hero(w, h, L, self._hero_image, self._logo_image, logo_xy)
        self._photo = ImageTk.PhotoImage(img)  # garder la référence
        c = self.canvas
        c.delete("all")
        c.create_image(0, 0, image=self._photo, anchor="nw")

        # titre (+ séparateur vertical si logo)
        tx = x0
        if lw:
            sx = x0 + lw + gap
            c.create_line(sx, L["head_y"] - int(lh * 0.45),
                          sx, L["head_y"] + int(lh * 0.45),
                          fill=COLORS["brand"], width=2)
            tx = sx + 2 + gap
        c.create_text(tx, L["head_y"], text="AJI TSTAJI", anchor="w",
                      fill=COLORS["brand"], font=title_font)

        # phrase d'accroche
        c.create_text(cx, L["tag_y"],
                      text="Trouvez votre prochaine opportunité\n"
                           "professionnelle à Marrakech",
                      fill=COLORS["brand"], font=(FONT, L["tag_pt"]),
                      justify="center")

        # petite barre + légende sous la photo
        c.create_line(cx - 22, L["bar_y"], cx + 22, L["bar_y"],
                      fill=COLORS["primary"], width=3)
        c.create_text(cx, L["cap_y"],
                      text="Trouvez les opportunités\nqui correspondent à votre avenir",
                      fill=COLORS["brand"], font=(FONT, L["cap_pt"]),
                      justify="center")

    # ------------------------------------------------------------ droite
    def _build_right(self):
        right = ctk.CTkFrame(self, fg_color=COLORS["bg"], corner_radius=0)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_rowconfigure(0, weight=1)
        right.grid_columnconfigure(0, weight=1)

        form = ctk.CTkFrame(right, fg_color="transparent", width=380)
        form.grid(row=0, column=0)

        ctk.CTkLabel(form, text="Connexion", anchor="w",
                     font=ctk.CTkFont(FONT, 30, "bold"),
                     text_color=COLORS["text"]).pack(fill="x")
        ctk.CTkLabel(form, text="Accédez à votre espace personnel", anchor="w",
                     font=ctk.CTkFont(FONT, 13),
                     text_color=COLORS["text_muted"]).pack(fill="x", pady=(2, 28))

        # E-mail
        self._field_label(form, "Adresse e-mail")
        self.email_box, self.email = self._make_field(form, "utilisateur@example.com")
        self.email_box.pack(fill="x", pady=(6, 16))

        # Mot de passe
        self._field_label(form, "Mot de passe")
        self.pwd_box, self.password = self._make_field(
            form, "••••••••", secret=True)
        self.pwd_box.pack(fill="x", pady=(6, 0))

        self.toggle_btn = ctk.CTkButton(
            self.pwd_box, text="Afficher", width=64, height=30,
            fg_color="transparent", hover_color=COLORS["primary_light"],
            text_color=COLORS["primary"], font=ctk.CTkFont(FONT, 12, "bold"),
            command=self._toggle_password)
        self.toggle_btn.pack(side="right", padx=(0, 6))

        # Message d'erreur
        self.error_label = ctk.CTkLabel(
            form, text="", anchor="w", justify="left", wraplength=380,
            font=ctk.CTkFont(FONT, 12), text_color=COLORS["error"])
        self.error_label.pack(fill="x", pady=(10, 0))

        # Lien « Mot de passe oublié ? »
        ctk.CTkButton(
            form, text="Mot de passe oublié ?", height=24, width=0,
            fg_color="transparent", hover_color=COLORS["primary_light"],
            text_color=COLORS["primary"], anchor="e",
            font=ctk.CTkFont(FONT, 12, "bold"),
            command=self._forgot).pack(anchor="e", pady=(4, 14))

        # Bouton principal
        self.login_btn = ctk.CTkButton(
            form, text="Se connecter  →", height=46, corner_radius=10,
            fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"],
            font=ctk.CTkFont(FONT, 14, "bold"), command=self._submit)
        self.login_btn.pack(fill="x")

        # Séparateur « ou »
        sep = ctk.CTkFrame(form, fg_color="transparent")
        sep.pack(fill="x", pady=18)
        sep.grid_columnconfigure((0, 2), weight=1)
        for col in (0, 2):
            ctk.CTkFrame(sep, height=1, fg_color=COLORS["border"]).grid(
                row=0, column=col, sticky="ew")
        ctk.CTkLabel(sep, text="ou", text_color=COLORS["text_muted"],
                     font=ctk.CTkFont(FONT, 12)).grid(row=0, column=1, padx=12)

        # Créer un compte
        ctk.CTkButton(
            form, text="Créer un compte", height=46, corner_radius=10,
            fg_color="transparent", hover_color=COLORS["primary_light"],
            border_width=1, border_color=COLORS["primary"],
            text_color=COLORS["primary"], font=ctk.CTkFont(FONT, 14, "bold"),
            command=self._register).pack(fill="x")

        ctk.CTkLabel(right, text="© AJI TSTAJI", font=ctk.CTkFont(FONT, 11),
                     text_color=COLORS["text_muted"]).grid(
            row=1, column=0, pady=(0, 14))

        # Touche Entrée + focus initial
        for w in (self.email, self.password):
            w.bind("<Return>", lambda e: self._submit())
        self.after(200, lambda: self.email.focus_set())

    # ------------------------------------------------------------ helpers UI
    def _field_label(self, parent, text):
        ctk.CTkLabel(parent, text=text, anchor="w",
                     font=ctk.CTkFont(FONT, 12, "bold"),
                     text_color=COLORS["text"]).pack(fill="x")

    def _make_field(self, parent, placeholder, secret=False):
        box = ctk.CTkFrame(parent, height=46, corner_radius=10,
                           fg_color=COLORS["input_bg"],
                           border_width=1, border_color=COLORS["border"])
        box.pack_propagate(False)
        entry = ctk.CTkEntry(
            box, placeholder_text=placeholder, height=40, border_width=0,
            fg_color="transparent", text_color=COLORS["text"],
            placeholder_text_color=COLORS["text_muted"],
            font=ctk.CTkFont(FONT, 13), show="•" if secret else "")
        entry.pack(side="left", fill="both", expand=True, padx=(10, 4), pady=2)
        entry.bind("<FocusIn>", lambda e: box.configure(
            border_color=COLORS["primary"], border_width=2))
        entry.bind("<FocusOut>", lambda e: box.configure(
            border_color=COLORS["border"], border_width=1))
        return box, entry

    def _toggle_password(self):
        self._pwd_visible = not self._pwd_visible
        self.password.configure(show="" if self._pwd_visible else "•")
        self.toggle_btn.configure(
            text="Masquer" if self._pwd_visible else "Afficher")

    # ------------------------------------------------------------ actions
    def show_error(self, message):
        self.error_label.configure(text=message)

    def set_loading(self, loading):
        self.login_btn.configure(
            state="disabled" if loading else "normal",
            text="Connexion…" if loading else "Se connecter  →")

    def clear(self):
        self.email.delete(0, "end")
        self.password.delete(0, "end")
        self.show_error("")

    def _submit(self):
        email = self.email.get().strip()
        pwd = self.password.get()
        if not email or not pwd:
            return self.show_error("Veuillez renseigner l'e-mail et le mot de passe.")
        if not EMAIL_RE.match(email):
            return self.show_error("Adresse e-mail invalide.")
        self.show_error("")
        self.set_loading(True)
        self.after(50, lambda: self._authenticate(email, pwd))

    def _authenticate(self, email, pwd):
        try:
            result = self._on_login(email, pwd)
        except Exception as exc:  # message de votre backend / base de données
            self.set_loading(False)
            return self.show_error(str(exc) or "Erreur de connexion.")
        self.set_loading(False)

        ok, msg = True, ""
        if isinstance(result, tuple):
            ok, msg = result[0], (result[1] if len(result) > 1 else "")
        elif result is False:
            ok = False
        if not ok:
            return self.show_error(msg or "E-mail ou mot de passe incorrect.")
        if self._on_success:
            self._on_success()

    def _register(self):
        if self._on_register:
            self._on_register()

    def _forgot(self):
        if self._on_forgot:
            self._on_forgot()


# ----------------------------------------------------------------------------
# Aperçu rapide pour tester le design uniquement (ne pas utiliser en prod)
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    root = ctk.CTk()
    root.title("AJI TSTAJI")
    root.geometry("1100x680")
    root.minsize(900, 600)
    page = LoginPage(root, on_login=lambda e, p: (p == "test", "Identifiants invalides"),
                     on_success=lambda: print("Connecté"))
    page.pack(fill="both", expand=True)
    root.mainloop()

/*
 * Liste des animations de l'écran périphérique, dans l'ordre :
 * ANIM_SEL 0 = première ligne, ANIM_SEL 1 = deuxième, etc.
 * ANIM_NXT / ANIM_PRV parcourent cette liste en boucle.
 *
 * Mis à jour par tools/anim_to_c.py ; on peut réordonner les lignes à la main.
 * Chaque NVG_ANIM(nom) correspond à assets/anim_<nom>.c.
 */
NVG_ANIM(crystal)
NVG_ANIM(rain)
NVG_ANIM(waves)
NVG_ANIM(stars)
NVG_ANIM(cube)

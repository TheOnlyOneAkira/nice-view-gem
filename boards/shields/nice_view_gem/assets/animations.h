#pragma once

#include <lvgl.h>
#include <stdint.h>
#include <zephyr/sys/util.h>

/*
 * Une animation de l'écran périphérique.
 * Les fichiers assets/anim_<nom>.c sont générés par tools/anim_to_c.py
 * (sauf anim_crystal.c, l'animation d'origine).
 */
struct nvg_animation {
    const char *name;
    const lv_image_dsc_t *const *frames;
    uint8_t frame_count;
    uint16_t duration_ms; /* durée d'une boucle complète */
    int16_t x;            /* position dans l'écran (160 x 68, zone libre : x 0..91) */
    int16_t y;
};

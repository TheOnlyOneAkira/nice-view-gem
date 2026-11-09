/*
 * Actions du behavior &anim (écran nice!view gem).
 *
 *   &anim ANIM_NXT     animation suivante
 *   &anim ANIM_PRV     animation précédente
 *   &anim ANIM_SEL 2   animation n° 2 (ordre de assets/anim_registry.h, à partir de 0)
 *   &anim ANIM_TOG     animation <-> image fixe
 *   &anim ANIM_ON      animation
 *   &anim ANIM_OFF     image fixe
 */
#pragma once

#define ANIM_NXT_CMD 0
#define ANIM_PRV_CMD 1
#define ANIM_SEL_CMD 2
#define ANIM_TOG_CMD 3
#define ANIM_ON_CMD 4
#define ANIM_OFF_CMD 5

#define ANIM_NXT ANIM_NXT_CMD 0
#define ANIM_PRV ANIM_PRV_CMD 0
#define ANIM_SEL ANIM_SEL_CMD
#define ANIM_TOG ANIM_TOG_CMD 0
#define ANIM_ON ANIM_ON_CMD 0
#define ANIM_OFF ANIM_OFF_CMD 0

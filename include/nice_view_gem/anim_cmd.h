#pragma once

#include <stdint.h>

/* Appelé par le behavior &anim (param1 = commande ANIM_*_CMD, param2 = argument). */
typedef void (*nice_view_anim_handler_t)(uint8_t cmd, uint8_t param);

/* Enregistré par l'écran périphérique ; sans écran, le behavior ne fait rien. */
void nice_view_anim_set_handler(nice_view_anim_handler_t handler);

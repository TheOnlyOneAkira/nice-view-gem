/*
 * Behavior &anim : change l'animation de l'écran nice!view gem.
 *
 * Locality GLOBAL : le central (moitié gauche) l'exécute chez lui ET le
 * transmet à la moitié droite, quelle que soit la moitié où se trouve la
 * touche. Seule la moitié qui affiche l'animation enregistre un handler.
 *
 * SPDX-License-Identifier: MIT
 */

#define DT_DRV_COMPAT zmk_behavior_nice_view_anim

#include <zephyr/device.h>
#include <zephyr/logging/log.h>
#include <drivers/behavior.h>
#include <zmk/behavior.h>

#include <nice_view_gem/anim_cmd.h>

LOG_MODULE_DECLARE(zmk, CONFIG_ZMK_LOG_LEVEL);

#if DT_HAS_COMPAT_STATUS_OKAY(DT_DRV_COMPAT)

static nice_view_anim_handler_t anim_handler;

void nice_view_anim_set_handler(nice_view_anim_handler_t handler) { anim_handler = handler; }

static int on_keymap_binding_pressed(struct zmk_behavior_binding *binding,
                                     struct zmk_behavior_binding_event event) {
    LOG_DBG("anim cmd %d param %d", binding->param1, binding->param2);
    if (anim_handler) {
        anim_handler((uint8_t)binding->param1, (uint8_t)binding->param2);
    }
    return ZMK_BEHAVIOR_OPAQUE;
}

static int on_keymap_binding_released(struct zmk_behavior_binding *binding,
                                      struct zmk_behavior_binding_event event) {
    return ZMK_BEHAVIOR_OPAQUE;
}

static const struct behavior_driver_api behavior_nice_view_anim_driver_api = {
    .binding_pressed = on_keymap_binding_pressed,
    .binding_released = on_keymap_binding_released,
    .locality = BEHAVIOR_LOCALITY_GLOBAL,
};

BEHAVIOR_DT_INST_DEFINE(0, NULL, NULL, NULL, NULL, POST_KERNEL, CONFIG_KERNEL_INIT_PRIORITY_DEFAULT,
                        &behavior_nice_view_anim_driver_api);

#endif /* DT_HAS_COMPAT_STATUS_OKAY(DT_DRV_COMPAT) */

/*
 * Animations de l'écran périphérique, avec changement à chaud par le
 * behavior &anim (voir include/dt-bindings/zmk/nice_view_anim.h).
 *
 * L'ordre des animations (numéro pour ANIM_SEL) est celui de
 * assets/anim_registry.h. Le choix (animation + animé/fixe) est mémorisé
 * dans les réglages de la moitié qui affiche l'animation.
 */
#include <stdlib.h>
#include <zephyr/kernel.h>
#include <zephyr/settings/settings.h>
#include <zephyr/logging/log.h>
#include <zmk/display.h>
#include <dt-bindings/zmk/nice_view_anim.h>
#include <nice_view_gem/anim_cmd.h>
#include "animation.h"

LOG_MODULE_DECLARE(zmk, CONFIG_ZMK_LOG_LEVEL);

#define NVG_ANIM(name) extern const struct nvg_animation nvg_anim_##name;
#include "../assets/anim_registry.h"
#undef NVG_ANIM

#define NVG_ANIM(name) &nvg_anim_##name,
static const struct nvg_animation *const animations[] = {
#include "../assets/anim_registry.h"
};
#undef NVG_ANIM

#define ANIM_COUNT ARRAY_SIZE(animations)

/* Commande interne : restauration des réglages (param = index | animé << 7) */
#define ANIM_RESTORE_CMD 0x80

struct anim_cmd {
    uint8_t cmd;
    uint8_t param;
};

K_MSGQ_DEFINE(anim_cmd_q, sizeof(struct anim_cmd), 8, 1);

static lv_obj_t *art;
static uint8_t current = CONFIG_NICE_VIEW_GEM_ANIMATION_DEFAULT % ANIM_COUNT;
static bool animated = IS_ENABLED(CONFIG_NICE_VIEW_GEM_ANIMATION);
static uint32_t random_seed;

static uint8_t static_frame(const struct nvg_animation *a) {
    if (CONFIG_NICE_VIEW_GEM_ANIMATION_FRAME > 0) {
        return (CONFIG_NICE_VIEW_GEM_ANIMATION_FRAME - 1) % a->frame_count;
    }
    return random_seed % a->frame_count;
}

/* À appeler depuis la file d'affichage (thread LVGL). */
static void apply(void) {
    if (art == NULL) {
        return;
    }
    const struct nvg_animation *a = animations[current];

    lv_anim_delete(art, NULL);
    lv_animimg_set_src(art, (const void **)a->frames, a->frame_count);
    lv_obj_align(art, LV_ALIGN_TOP_LEFT, a->x, a->y);

    if (animated && a->frame_count > 1) {
        lv_animimg_set_duration(art, a->duration_ms);
        lv_animimg_set_repeat_count(art, LV_ANIM_REPEAT_INFINITE);
        lv_animimg_start(art);
    } else {
        lv_image_set_src(art, a->frames[static_frame(a)]);
    }
}

#if IS_ENABLED(CONFIG_SETTINGS)
struct anim_saved {
    uint8_t index;
    uint8_t animated;
};

static void save_work_handler(struct k_work *work) {
    struct anim_saved s = {.index = current, .animated = animated};
    int err = settings_save_one("nvg_anim/state", &s, sizeof(s));
    if (err < 0) {
        LOG_ERR("nice_view_gem: sauvegarde de l'animation impossible (%d)", err);
    }
}

static K_WORK_DELAYABLE_DEFINE(save_work, save_work_handler);
#endif

static void cmd_work_handler(struct k_work *work) {
    struct anim_cmd c;
    bool changed = false;

    while (k_msgq_get(&anim_cmd_q, &c, K_NO_WAIT) == 0) {
        switch (c.cmd) {
        case ANIM_NXT_CMD:
            current = (current + 1) % ANIM_COUNT;
            break;
        case ANIM_PRV_CMD:
            current = (current + ANIM_COUNT - 1) % ANIM_COUNT;
            break;
        case ANIM_SEL_CMD:
            if (c.param >= ANIM_COUNT) {
                continue;
            }
            current = c.param;
            break;
        case ANIM_TOG_CMD:
            animated = !animated;
            break;
        case ANIM_ON_CMD:
            animated = true;
            break;
        case ANIM_OFF_CMD:
            animated = false;
            break;
        case ANIM_RESTORE_CMD:
            current = (c.param & 0x7f) % ANIM_COUNT;
            animated = (c.param & 0x80) != 0;
            apply();
            continue; /* rien à resauvegarder */
        default:
            continue;
        }
        changed = true;
    }

    if (changed) {
        apply();
#if IS_ENABLED(CONFIG_SETTINGS)
        /* Délai pour ne pas user la flash si on enchaîne les appuis */
        k_work_reschedule(&save_work, K_SECONDS(10));
#endif
    }
}

static K_WORK_DEFINE(cmd_work, cmd_work_handler);

static void push_cmd(uint8_t cmd, uint8_t param) {
    struct anim_cmd c = {.cmd = cmd, .param = param};
    if (k_msgq_put(&anim_cmd_q, &c, K_NO_WAIT) != 0) {
        LOG_WRN("nice_view_gem: file de commandes d'animation pleine");
        return;
    }
    k_work_submit_to_queue(zmk_display_work_q(), &cmd_work);
}

#if IS_ENABLED(CONFIG_SETTINGS)
static int anim_settings_set(const char *name, size_t len, settings_read_cb read_cb,
                             void *cb_arg) {
    if (!settings_name_steq(name, "state", NULL)) {
        return -ENOENT;
    }
    struct anim_saved s;
    if (len != sizeof(s)) {
        return -EINVAL;
    }
    int rc = read_cb(cb_arg, &s, sizeof(s));
    if (rc < 0) {
        return rc;
    }
    push_cmd(ANIM_RESTORE_CMD, (s.index & 0x7f) | (s.animated ? 0x80 : 0));
    return 0;
}

SETTINGS_STATIC_HANDLER_DEFINE(nvg_anim, "nvg_anim", NULL, anim_settings_set, NULL, NULL);
#endif

void draw_animation(lv_obj_t *canvas) {
    srand(k_uptime_get_32());
    random_seed = (uint32_t)rand();

    art = lv_animimg_create(canvas);
    apply();

#if IS_ENABLED(CONFIG_ZMK_BEHAVIOR_NICE_VIEW_ANIM)
    nice_view_anim_set_handler(push_cmd);
#endif
    /* Applique un réglage restauré avant la création de l'écran */
    k_work_submit_to_queue(zmk_display_work_q(), &cmd_work);
}

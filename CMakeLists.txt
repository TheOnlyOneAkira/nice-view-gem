# Behavior &anim (changement d'animation de l'écran). Compilé dès que le
# keymap déclare un nœud "zmk,behavior-nice-view-anim", sur les deux moitiés,
# même sans écran nice_view_gem (il ne fait alors rien).
zephyr_include_directories(include)

if(CONFIG_ZMK_BEHAVIOR_NICE_VIEW_ANIM)
  target_sources(app PRIVATE src/behaviors/behavior_nice_view_anim.c)
endif()

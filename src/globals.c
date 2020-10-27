/************ Copyright Krono-Safe S.A. 2020, All rights reserved ************/

#include <app.h>

/* This data will be duplicated for each task by kspart. It must be placed in
 * shared SRAM so the hardware resource is shared (not the data themselves) */
float global_noise_matrix[IMG_W][IMG_H];

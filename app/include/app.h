/************ Copyright Krono-Safe S.A. 2020, All rights reserved ************/

#ifndef APP_H__
#define APP_H__

#include <stdint.h>
#include <stddef.h>

#define IMG_W 100
#define IMG_H 100

#define SWITCH_TO_G10 0
#define SWITCH_TO_G7 1
#define SWITCH_TO_G2 2
#define SWITCH_TO_G12 3

#define SWITCH_TO_H8  0
#define SWITCH_TO_H10 1
#define SWITCH_TO_H12 2

struct h_control {
  signed char work_iterations;
  signed char cond_h2_or_h5;
  signed char cond_h4_or_h9;
  signed char switch_value;
};


struct g_control {
  signed char work_iterations;
  signed char switch_value;
  signed char cond_g14_or_g15;
};

uint32_t crc32(const void *const data, size_t len);
void filter(float noise[IMG_H][IMG_W], unsigned char image[IMG_H][IMG_W]);
void filter2(float noise[IMG_H][IMG_W], unsigned char image[IMG_H][IMG_W]);

#define GEN_WORK(Seed, Filter, NoiseMat, Img, Iterations, Counter) \
  { \
    int nb_iterations = (Iterations); \
    int seed_size = 0; \
    for (; Seed[seed_size] != '\0'; seed_size++) {} \
    const uint32_t ss = crc32(Seed, seed_size); \
    nb_iterations += ((ss >> (ss & 0xf)) & 0xf); \
    for (int runs = 0; runs < nb_iterations; runs++) { \
      const uint32_t s = crc32(Seed, seed_size); \
      int shift = 0; \
      int max = ((IMG_H + (int)Counter + 60) % IMG_H + 1); \
      for (int i = 0; i  < max; i++) { \
        for (int j = 0; j < IMG_W; j++) { \
          const float f = (float)((s >> shift) & 0xff) / 255.0f; \
          NoiseMat[i][j] = f; \
          shift = (shift + 1) % 6; \
        } \
      } \
      Filter(NoiseMat, Img); \
    } \
    Counter += 1u; \
  }

#  pragma section CODE_FAR ".text_vle" far-absolute RX
#  pragma use_section CODE_FAR filter2

#endif /* ! APP_H__ */

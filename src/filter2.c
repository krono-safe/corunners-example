/************ Copyright Krono-Safe S.A. 2020, All rights reserved ************/

#include <app.h>

#define FILTER_H 3
#define FILTER_W 3

static const float _filter2[3][3] =
{
  { -1.0f, -1.0f, -1.0f, },
  { -1.0f, +9.0f, -1.0f, },
  { -1.0f, -1.0f, -1.0f, },
};

void filter2(float noise[IMG_H][IMG_W], unsigned char image[IMG_H][IMG_W])
{
  /* Don't apply the filter on the outermost frame of pixels (to avoid
   * bounds checking) */
  for (int j = 1; j < IMG_H - 1; j++)
  {
    for (int i = 1; i < IMG_W - 1; i++)
    {
      float col = 0.0f;
      for (int fy = -1; fy <= +1; fy++)
      {
        for (int fx = -1; fx <= +1; fx++)
        {
          /* [-1 ... +1] ==> [0... +2] ==> [0 ... +1] */
          const float norm = ((noise[fy + j][fx + i] + 1.0f) / 2.0f) * 255.0f;
          const float val = norm * _filter2[fy+1][fx+1];
          col += val;
        }
      }
      image[j][i] = (col > 255.0f)
        ? 255 /* Saturate! */
        : (unsigned char)(col);
    }
  }
}

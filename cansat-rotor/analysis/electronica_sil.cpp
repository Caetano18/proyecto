// =====================================================================================
//  electronica_sil.cpp — Prueba del firmware en la PC (software en el lazo, SIL).
//  Reproduce a 1 kHz los sensores del vuelo nominal simulado
//  (data/electronica_kalman_sensores.dat), envía comandos de tierra, modela el giro del
//  rotor (pulsos del sensor hall) y, opcionalmente, un reinicio del procesador.
//  Compilar:  g++ -std=gnu++17 -O2 -o /tmp/sil analysis/electronica_sil.cpp
//  Usar:      /tmp/sil analysis/data/electronica_kalman_sensores.dat [t_reinicio_s]
// =====================================================================================
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

static uint64_t g_us = 0, g_boot = 0;        // tiempo absoluto y del último arranque
uint32_t millis() { return (uint32_t)((g_us - g_boot) / 1000); }
uint32_t micros() { return (uint32_t)(g_us - g_boot); }
void delay(uint32_t ms) { g_us += (uint64_t)ms * 1000; }
void noInterrupts() {}
void interrupts() {}
#define SIL
#include "electronica_firmware.cpp"

struct Fila { double t, p, az; };
static std::vector<Fila> D;
static uint8_t fram[256];
static uint16_t servo_us = 0;
static double t_libera = -1;
static void (*isr)() = nullptr;
static uint64_t ult_kick = 0;
static double max_sin_kick = 0;
static int32_t rtc_ofs = 13 * 3600;          // la hora inicial del RTC
static int n_tlm = 0;
static bool imprimir = true;
struct Cmd { double t; const char* s; bool usado; };
static Cmd cmds[] = {{1.0, "CMD,1000,CX,ON", false},     {2.0, "CMD,1000,ST,13:35:59", false},
                     {2.5, "CMD,1000,MEC,LATCH,OFF", false}, {3.0, "CMD,1000,CAL", false},
                     {3.5, "CMD,1000,PWR,ON", false},     {40.0, "CMD,1000,CAL", false},
                     {41.0, "CMD,9999,MEC,LATCH,ON", false}};

static double T() { return g_us / 1e6; }
static const Fila& fila() {
  size_t i = (size_t)(g_us / 20000);
  return D[i < D.size() ? i : D.size() - 1];
}
float hal_baro_pa() { return (float)fila().p; }
float hal_baro_temp_c() { return 21.5f; }
void hal_imu(float a[3], float g[3]) {
  a[0] = 0.12f; a[1] = -0.05f; a[2] = (float)fila().az;
  g[0] = g[1] = 0; g[2] = (t_libera > 0) ? 4.0f : 0.0f;  // giro del cuerpo por rozamiento
}
bool hal_gps(Gps* g) {
  static uint64_t ult = 0;
  if (g_us - ult < 1000000) return false;
  ult = g_us;
  double h = 44330.77 * (1 - std::pow(fila().p / 101325.0, 0.190263));
  g->hora_s = (uint32_t)(13 * 3600 + 35 * 60 + 58 + T()); g->alt = (float)(120.0 + h);
  g->lat = -31.4201f; g->lon = -64.1888f; g->sats = 9; g->valido = true;
  return true;
}
float hal_vbat() { return 3.92f; }
float hal_ibat() { return t_libera > 0 ? 0.74f : 0.19f; }
float hal_solar_v() { return 2.35f; }
void hal_servo_us(uint16_t us) {
  if (us == SERVO_LIBRE_US && servo_us != SERVO_LIBRE_US && t_libera < 0 && T() > 10) {
    t_libera = T();
    std::printf("[%7.2f s] servo: LIBERAR\n", T());
  }
  servo_us = us;
}
void hal_servo_power(bool) {}
void hal_cam_power(bool) {}
bool hal_fram_read(uint16_t d, void* b, size_t n) { std::memcpy(b, fram + d, n); return true; }
bool hal_fram_write(uint16_t d, const void* b, size_t n) { std::memcpy(fram + d, b, n); return true; }
uint32_t hal_rtc_s() { return (uint32_t)(rtc_ofs + T()); }
void hal_rtc_set(uint32_t s) { rtc_ofs = (int32_t)s - (int32_t)T(); }
void hal_radio_send(const char* s) {
  n_tlm++;
  if (imprimir) std::printf("[%7.2f s] TX %s\n", T(), s);
}
int hal_radio_line(char* buf, size_t n) {
  for (auto& c : cmds)
    if (!c.usado && T() >= c.t) {
      c.usado = true; std::snprintf(buf, n, "%s", c.s);
      std::printf("[%7.2f s] RX %s\n", T(), c.s);
      return 1;
    }
  return 0;
}
void hal_sd_log(const char* s) {
  if (s[0] == '#') std::printf("[%7.2f s] estado %s\n", T(), s + 5);
}
void hal_wdt_begin(uint32_t) { ult_kick = g_us; }
void hal_wdt_kick() {
  max_sin_kick = std::fmax(max_sin_kick, (g_us - ult_kick) / 1e3);
  ult_kick = g_us;
}
void hal_hall_attach(void (*f)()) { isr = f; }

// reinicia todas las variables globales del firmware (equivale a un reinicio del MCU)
static void reiniciar_firmware() {
  kf = Kalman(); rpm_f = 0; u_ult = 0; sim_p = NAN; hmax_corrida = -1e9f; t_s = 0;
  t_desp = t_apo = t_cond = t_v1 = t_quieto = t_lib = t_giro = 1e9f; t_estado = 0;
  choque = sim_hab = baro_falla = false; n_desp = 0; n_falla_baro = 0;
  p_ult = p_media = NAN; t_disc = t_sacude = 1e9f; gps_h0 = NAN; gps_hmax = -1e9f;
  std::strcpy(eco, "NINGUNO"); std::memset(&P, 0, sizeof P);
  isr_t = isr_per = isr_n = 0;
}

int main(int argc, char** argv) {
  const char* ruta = argc > 1 ? argv[1] : "analysis/data/electronica_kalman_sensores.dat";
  double t_reset = argc > 2 ? std::atof(argv[2]) : -1;
  FILE* f = std::fopen(ruta, "r");
  if (!f) { std::perror(ruta); return 1; }
  char lin[128];
  if (!std::fgets(lin, sizeof lin, f)) return 1;
  Fila r;
  while (std::fscanf(f, "%lf %lf %lf", &r.t, &r.p, &r.az) == 3) D.push_back(r);
  std::fclose(f);
  std::memset(fram, 0xFF, sizeof fram);
  setup();
  double ang = 0;                                // ángulo del rotor [vueltas]
  bool reiniciado = false, parado = false;
  double t_parado_reportado = -1;
  const double t_fin = D.back().t;
  while (T() < t_fin) {
    g_us += 1000;
    imprimir = n_tlm < 4 || (T() > 16 && T() < 31 && n_tlm % 3 == 0) || T() > t_fin - 2;
    double h_baro = 44330.77 * (1 - std::pow(fila().p / 101325.0, 0.190263));
    if (t_libera > 0 && !parado && T() > t_libera + 10 && h_baro < 0.5) {
      parado = true;                                       // contacto con el suelo
      std::printf("[%7.2f s] el rotor se detiene en el suelo\n", T());
    }
    if (t_libera > 0 && !parado && T() > t_libera + 0.15) { // arranque del rotor
      double rpm = 1150.0 * (1 - std::exp(-(T() - t_libera - 0.15) / 1.5));
      double ant = ang;
      ang += rpm / 60.0 * 1e-3;
      if (std::floor(ang * IMANES) > std::floor(ant * IMANES) && isr) isr();
    }
    if (t_reset > 0 && !reiniciado && T() >= t_reset) {
      reiniciado = true;
      std::printf("[%7.2f s] *** REINICIO DEL PROCESADOR (0,3 s sin energía) ***\n", T());
      reiniciar_firmware();
      g_us += 300000; g_boot = g_us;
      setup();
      std::printf("[%7.2f s] recuperado en estado %s, h_max=%.1f m, latch=%u\n", T(),
                  NOMBRE[P.estado], P.h_max, P.latch);
    }
    loop();
    if (parado && rpm_f == 0 && t_parado_reportado < 0) {
      t_parado_reportado = T();
      std::printf("[%7.2f s] firmware: rotor detenido (ROTOR_RPM = 0)\n", T());
    }
  }
  std::printf("paquetes enviados %d, PACKET_COUNT %u, máx. intervalo sin patear el perro "
              "guardián %.0f ms\n", n_tlm, P.packet_count, max_sin_kick);
  return 0;
}

// =====================================================================================
//  electronica_firmware.cpp — Núcleo del software de vuelo del CanSat con rotor libre
//  Arduino / PlatformIO, MCU Cortex-M de 3,3 V. Contiene la lógica completa: estimador,
//  máquina de estados, persistencia (F1, F2, F5), parser de comandos, telemetría y rpm.
//  Las funciones hal_* encapsulan el hardware y se implementan aparte (hal.cpp) con las
//  bibliotecas de cada componente. En ARM con newlib-nano, compilar con
//  -u _printf_float para que snprintf formatee números reales.
// =====================================================================================
#ifndef SIL
#include <Arduino.h>                 // en la PC (prueba SIL) lo reemplaza el banco
#endif
#include <math.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// ------------------------------------------------------------------ configuración
#define TEAM_ID "1000"                          // número asignado al equipo
static const uint32_t T_CONTROL_MS = 20;        // lazo de control a 50 Hz
static const uint32_t T_TLM_MS = 1000;          // telemetría a 1 Hz (X5)
static const float G0 = 9.80665f;
static const float SIG_A = 0.5f, SIG_A_MOTOR = 5.0f, SIG_A_SIM = 3.0f; // m/s2
static const float SIG_B = 0.3f;                // m, ruido efectivo del barómetro
static const float COMPUERTA = 25.0f;           // chi2, 5 sigma
static const uint16_t N_REANCLA = 50;           // 1 s de rechazos seguidos
static const float T_BLOQUEO = 4.0f;            // s sin apogeo después del despegue
static const float T_PERSIST = 0.2f;            // s de persistencia de condiciones
static const float FRACCION = 0.80f;            // C4: 80 % de la altitud máxima
static const float V_LIM = 40.0f, V_TIMER = 10.0f;  // m/s, ver capítulo
static const float CHOQUE_G = 6.0f;             // umbral de choque de expulsión
static const uint16_t SERVO_TRABA_US = 1100, SERVO_LIBRE_US = 1350;  // anillo 15 grados
static const float RPM_CONFIRMA = 600.0f;       // giro confirmado (PAYLOAD_RELEASE)
static const uint32_t T_ARRANQUE_MS = 8000;     // espera de giro antes de reintentar
static const uint8_t MAX_REINTENTOS = 2;
static const uint8_t IMANES = 2;                // imanes en el cubo (balanceados)
static const uint32_t PERIODO_MIN_US = 4000;    // rechaza pulsos > 7500 rpm (rebotes)

enum Estado : uint8_t { LAUNCH_PAD, ASCENT, APOGEE, DESCENT, PROBE_RELEASE,
                        PAYLOAD_RELEASE, LANDED };
static const char* const NOMBRE[] = {"LAUNCH_PAD", "ASCENT", "APOGEE", "DESCENT",
                                     "PROBE_RELEASE", "PAYLOAD_RELEASE", "LANDED"};

// ------------------------------------------------------------------ hardware (hal.cpp)
struct Gps { uint32_t hora_s; float alt, lat, lon; uint8_t sats; bool valido; };
float hal_baro_pa();                             // presión [Pa]; NAN si falla
float hal_baro_temp_c();
void hal_imu(float acc[3], float gyr[3]);        // m/s2 y grados/s; +Z hacia el nadir
bool hal_gps(Gps* g);                            // true si hay dato nuevo
float hal_vbat();                                // V (INA219)
float hal_ibat();                                // A (INA219, shunt 20 mOhm)
float hal_solar_v();                             // V del panel (divisor al ADC)
void hal_servo_us(uint16_t us);
void hal_servo_power(bool on);                   // MOSFET del riel del servo
void hal_cam_power(bool on);
bool hal_fram_read(uint16_t dir, void* buf, size_t n);
bool hal_fram_write(uint16_t dir, const void* buf, size_t n);
uint32_t hal_rtc_s();                            // segundos UTC del día (RTC con pila)
void hal_rtc_set(uint32_t s);
void hal_radio_send(const char* s);              // XBee unicast (X2, X3)
int hal_radio_line(char* buf, size_t n);         // >0 si llegó una línea completa
void hal_sd_log(const char* s);                  // con búfer, no bloqueante
void hal_wdt_begin(uint32_t ms);
void hal_wdt_kick();
void hal_hall_attach(void (*isr)());             // flanco de bajada, pull-up 10 k

// ------------------------------------------------------------------ persistencia (F1, F5)
struct Persist {
  uint32_t magic, seq;
  uint8_t estado, latch, modo_sim, cx_on, pwr_extra, reintentos, rsv[2];
  uint32_t packet_count;
  float p0, h_max, h_ult;
  uint32_t t_apogeo_s;   // hora UTC del apogeo (RTC), para el temporizador de respaldo
  uint32_t crc;
};
static const uint32_t MAGIA = 0xCA5A7026u;
static Persist P;

static uint32_t crc32(const uint8_t* d, size_t n) {
  uint32_t c = 0xFFFFFFFFu;
  while (n--) { c ^= *d++; for (int k = 0; k < 8; k++) c = (c >> 1) ^ (0xEDB88320u & -(c & 1u)); }
  return ~c;
}
static void persist_guardar() {           // dos copias alternadas: un corte a mitad de
  P.seq++;                                 // escritura deja intacta la otra
  P.magic = MAGIA;
  P.crc = crc32((const uint8_t*)&P, offsetof(Persist, crc));
  hal_fram_write((P.seq & 1u) ? 64 : 0, &P, sizeof P);
}
static bool persist_cargar() {
  Persist a, b;
  bool va = hal_fram_read(0, &a, sizeof a) && a.magic == MAGIA &&
            a.crc == crc32((const uint8_t*)&a, offsetof(Persist, crc));
  bool vb = hal_fram_read(64, &b, sizeof b) && b.magic == MAGIA &&
            b.crc == crc32((const uint8_t*)&b, offsetof(Persist, crc));
  if (!va && !vb) return false;
  P = (va && (!vb || a.seq > b.seq)) ? a : b;
  return true;
}

// ------------------------------------------------------------------ estimador
struct Kalman {
  float h, v, P00, P01, P11;
  uint16_t rech;
  void init(float h0) { h = h0; v = 0; P00 = 1; P01 = 0; P11 = 1e4f; rech = 0; } // v libre
  void predecir(float u, float dt, float sa) {
    float q = sa * sa, dt2 = dt * dt;
    h += v * dt + 0.5f * u * dt2;
    v += u * dt;
    P00 += 2 * dt * P01 + dt2 * P11 + q * dt2 * dt2 / 4;
    P01 += dt * P11 + q * dt2 * dt / 2;
    P11 += q * dt2;
  }
  bool corregir(float z, float sb) {     // devuelve false si la medición se rechaza
    float nu = z - h, S = P00 + sb * sb;
    if (nu * nu > COMPUERTA * S) {
      if (++rech < N_REANCLA) return false;
      P00 += nu * nu; S = P00 + sb * sb;    // re-anclaje tras 1 s de rechazos
    }
    rech = 0;
    float K0 = P00 / S, K1 = P01 / S;
    h += K0 * nu; v += K1 * nu;
    P11 -= K1 * P01; P01 *= (1 - K0); P00 *= (1 - K0);
    return true;
  }
};
static Kalman kf;

static float altura_isa(float p, float p0) {    // m sobre la referencia de CAL
  return 44330.77f * (1.0f - powf(p / p0, 0.190263f));
}

// ------------------------------------------------------------------ rpm por interrupción
static volatile uint32_t isr_t = 0, isr_per = 0, isr_n = 0;
static void isr_hall() {
  uint32_t t = micros(), p = t - isr_t;
  if (p < PERIODO_MIN_US) return;           // rebote o ruido: se descarta
  isr_t = t; isr_per = p; isr_n++;
}
static float rpm_f = 0;                     // rpm filtradas
static void rpm_actualizar() {              // llamada a 50 Hz
  static uint32_t n_ant = 0, per[3] = {0, 0, 0};
  static uint8_t k = 0;
  noInterrupts();
  uint32_t t = isr_t, p = isr_per, n = isr_n;
  interrupts();
  if (n != n_ant) { per[k] = p; k = (k + 1) % 3; n_ant = n; }
  uint32_t a = per[0], b = per[1], c = per[2];             // mediana de 3
  uint32_t med = (a > b) ? ((b > c) ? b : ((a > c) ? c : a)) : ((a > c) ? a : ((b > c) ? c : b));
  uint32_t espera = (med > 0) ? 3 * med : 0;
  if (espera < 500000u) espera = 500000u;
  if (espera > 1500000u) espera = 1500000u;
  if (med == 0 || (uint32_t)(micros() - t) > espera) { rpm_f = 0; return; } // detenido
  float rpm = 60.0e6f / (IMANES * (float)med);
  rpm_f += 0.3f * (rpm - rpm_f);
}

// ------------------------------------------------------------------ variables de vuelo
static float u_ult = 0, sim_p = NAN, hmax_corrida = -1e9f;
static float t_s = 0;                           // s desde el arranque del MCU
static float t_desp = 1e9f, t_apo = 1e9f, t_cond = 1e9f, t_v1 = 1e9f, t_quieto = 1e9f;
static float t_lib = 1e9f, t_giro = 1e9f, t_estado = 0;
static bool choque = false, sim_hab = false, baro_falla = false;
static uint8_t n_desp = 0;
static uint16_t n_falla_baro = 0;
static float acc[3], gyr[3], temp_c = 0, p_ult = NAN, p_media = NAN;
static float t_disc = 1e9f, t_sacude = 1e9f;
static Gps gps = {0, 0, 0, 0, 0, false};
static float gps_h0 = NAN, gps_hmax = -1e9f;
static char eco[24] = "NINGUNO";

static void cambiar(Estado e) {
  P.estado = e; t_estado = t_s;
  persist_guardar();
  char s[48]; snprintf(s, sizeof s, "#EVT,%.2f,%s", t_s, NOMBRE[e]); hal_sd_log(s);
}
static void traba(bool liberar) {
  P.latch = liberar ? 1 : 0;
  hal_servo_us(liberar ? SERVO_LIBRE_US : SERVO_TRABA_US);
  persist_guardar();
}

static void aterrizaje() {
  t_quieto = (fabsf(kf.v) < 0.5f && kf.h < 0.25f * P.h_max) ? fminf(t_quieto, t_s) : 1e9f;
  if (t_s - t_quieto >= 5.0f) cambiar(LANDED);
}

// ------------------------------------------------------------------ lazo de control 50 Hz
static void control(float dt) {
  t_s += dt;
  // 1) sensores
  float p = (P.modo_sim == 2) ? sim_p : hal_baro_pa();
  bool p_ok = !isnan(p) && p > 30000.0f && p < 110000.0f;
  if (P.modo_sim != 2) {
    n_falla_baro = p_ok ? 0 : n_falla_baro + 1;
    if (n_falla_baro > 25) baro_falla = true;             // 0,5 s sin lecturas válidas
  }
  if (p_ok) { p_ult = p; p_media = isnan(p_media) ? p : p_media + 0.02f * (p - p_media); }
  temp_c = hal_baro_temp_c();
  hal_imu(acc, gyr);
  float f_up = (P.modo_sim == 2) ? G0 : -acc[2];          // fuerza específica hacia arriba
  if (hal_gps(&gps) && gps.valido && gps.sats >= 6) {
    if (isnan(gps_h0) && P.estado == LAUNCH_PAD) gps_h0 = gps.alt;
    if (!isnan(gps_h0)) {
      gps_hmax = fmaxf(gps_hmax, gps.alt - gps_h0);
      bool disc = P.estado >= DESCENT && fabsf(kf.h - (gps.alt - gps_h0)) > 50.0f;
      t_disc = disc ? fminf(t_disc, t_s) : 1e9f;          // barómetro y GPS en desacuerdo
      if (t_s - t_disc > 3.0f) baro_falla = true;
    }
  }
  rpm_actualizar();

  // 2) estimador: la IMU es la entrada, el barómetro la medición
  bool en_vuelo = P.estado != LAUNCH_PAD && P.estado != LANDED;
  bool es_choque = en_vuelo && (t_s - t_desp > T_BLOQUEO) && fabsf(f_up) > CHOQUE_G * G0;
  choque |= es_choque;
  float u = es_choque ? u_ult : f_up - G0;
  u_ult = u;
  float sa = (P.modo_sim == 2) ? SIG_A_SIM
           : (es_choque ? 10.0f : ((t_s - t_desp < 2.6f) ? SIG_A_MOTOR : SIG_A));
  kf.predecir(u, dt, sa);
  if (p_ok) {
    kf.corregir(altura_isa(p, P.p0), SIG_B);
    if (P.modo_sim == 2) sim_p = NAN;                     // cada SIMP se usa una vez
  }

  // 3) máquina de estados
  switch (P.estado) {
    case LAUNCH_PAD:
      n_desp = (f_up > 2.0f * G0) ? n_desp + 1 : 0;      // 0,1 s a más de 2 g
      if (n_desp >= 5 || (kf.h > 15.0f && kf.v > 5.0f)) {
        t_desp = t_s; hmax_corrida = kf.h; P.h_max = kf.h;
        hal_cam_power(true);                              // C6, C7: video de todo el vuelo
        cambiar(ASCENT);
      }
      break;
    case ASCENT: {
      hmax_corrida = fmaxf(hmax_corrida, kf.h);
      static float t_g = 0;
      if (t_s - t_g > 0.2f) { P.h_max = hmax_corrida; P.h_ult = kf.h; persist_guardar(); t_g = t_s; }
      t_v1 = (kf.v < -1.0f) ? fminf(t_v1, t_s) : 1e9f;
      int votos = (t_s - t_v1 >= T_PERSIST) + (hmax_corrida - kf.h > 3.0f) + choque;
      bool convergido = kf.P11 < 4.0f;                    // sigma_v < 2 m/s
      if ((t_s - t_desp > T_BLOQUEO && convergido && votos >= 2) || t_s - t_desp > 40.0f) {
        P.h_max = hmax_corrida;
        if (baro_falla && !isnan(gps_h0)) P.h_max = gps_hmax;   // respaldo GPS
        P.t_apogeo_s = hal_rtc_s(); t_apo = t_s;
        P.cx_on = 1;                                      // X4: telemetría tras separarse
        cambiar(APOGEE);
      }
      break;
    }
    case APOGEE:                                          // visible al menos 1 paquete
      if (t_s - t_estado >= 1.0f) cambiar(DESCENT);
      break;
    case DESCENT: {
      bool cond = !baro_falla && (kf.h + kf.v * T_PERSIST <= FRACCION * P.h_max);
      t_cond = cond ? fminf(t_cond, t_s) : 1e9f;
      float desde = t_s - t_apo;
      bool por_baro = (t_s - t_cond >= T_PERSIST) && desde >= (1 - FRACCION) * P.h_max / V_LIM;
      bool por_tiempo = desde >= (1 - FRACCION) * P.h_max / V_TIMER + V_TIMER / G0 * logf(2.0f);
      if (por_baro || por_tiempo) {
        traba(true); t_lib = t_s; t_giro = 1e9f; P.reintentos = 0;
        cambiar(PROBE_RELEASE);
      }
      break;
    }
    case PROBE_RELEASE:
      t_giro = (rpm_f > RPM_CONFIRMA) ? fminf(t_giro, t_s) : 1e9f;
      if (t_s - t_giro >= 0.5f) { cambiar(PAYLOAD_RELEASE); break; }
      if ((t_s - t_lib) * 1000.0f > T_ARRANQUE_MS && P.reintentos < MAX_REINTENTOS) {
        P.reintentos++;                                   // sacude el anillo 0,3 s
        hal_servo_us(SERVO_TRABA_US); t_sacude = t_s; t_lib = t_s;
      }
      if (t_s - t_sacude >= 0.3f) { traba(true); t_sacude = 1e9f; }
      aterrizaje();                                       // también sin giro confirmado
      break;
    case PAYLOAD_RELEASE:
      aterrizaje();
      break;
    case LANDED:
      if (t_s - t_estado > 60.0f) hal_cam_power(false);
      break;
  }

  char s[160];                                            // registro a 50 Hz en la SD
  snprintf(s, sizeof s, "%.2f,%u,%.1f,%.2f,%.2f,%.3f,%.0f,%u", t_s, P.estado, p, kf.h, kf.v,
           u, rpm_f, P.latch);
  hal_sd_log(s);
}

// ------------------------------------------------------------------ comandos
static bool es(const char* a, const char* b) { return a && strcmp(a, b) == 0; }
static uint32_t hms(const char* s) {
  int h, m, x;
  return (s && sscanf(s, "%d:%d:%d", &h, &m, &x) == 3) ? (uint32_t)(h * 3600 + m * 60 + x)
                                                       : 0xFFFFFFFFu;
}
static void comando(char* linea) {
  char* tok[6] = {0};
  int n = 0;
  for (char* t = strtok(linea, ",\r\n"); t && n < 6; t = strtok(NULL, ",\r\n")) tok[n++] = t;
  if (n < 3 || !es(tok[0], "CMD") || !es(tok[1], TEAM_ID)) return;
  const char* c = tok[2];
  const char* a = tok[3];
  const char* b = tok[4];
  bool tierra = P.estado == LAUNCH_PAD || P.estado == LANDED;
  if (es(c, "CX") && (es(a, "ON") || es(a, "OFF"))) {
    P.cx_on = es(a, "ON");
  } else if (es(c, "ST") && a) {
    uint32_t s = es(a, "GPS") ? (gps.valido ? gps.hora_s : 0xFFFFFFFFu) : hms(a);
    if (s == 0xFFFFFFFFu) return;
    hal_rtc_set(s);
  } else if (es(c, "CAL")) {
    if (!tierra || isnan(p_media)) return;          // nunca en vuelo
    P.p0 = p_media;                                // media móvil de 1 s
    P.h_max = 0; P.packet_count = 0; P.estado = LAUNCH_PAD; P.reintentos = 0;
    kf.init(0); gps_h0 = NAN; choque = false; baro_falla = false;
  } else if (es(c, "MEC") && es(a, "LATCH") && (es(b, "ON") || es(b, "OFF"))) {
    if (es(b, "ON")) traba(true);                  // liberar: permitido siempre
    else if (P.estado == LAUNCH_PAD) traba(false); // trabar: solo en tierra
    else return;
  } else if (es(c, "MEC") && es(a, "CAM") && (es(b, "ON") || es(b, "OFF"))) {
    hal_cam_power(es(b, "ON"));
  } else if (es(c, "PWR") && (es(a, "ON") || es(a, "OFF"))) {  // X7: panel y batería
    P.pwr_extra = es(a, "ON");
  } else if (es(c, "SIM") && a) {                  // opcional, como en la guía 2025
    if (es(a, "ENABLE")) sim_hab = true;
    else if (es(a, "ACTIVATE") && sim_hab && P.estado == LAUNCH_PAD) P.modo_sim = 2;
    else if (es(a, "DISABLE")) { P.modo_sim = 0; sim_hab = false; }
    else return;
  } else if (es(c, "SIMP") && a && P.modo_sim == 2) {
    sim_p = (float)atof(a);
  } else {
    return;                                        // desconocido: sin eco
  }
  snprintf(eco, sizeof eco, "%s%s%s", c, a ? a : "", b ? b : "");  // sin comas
  persist_guardar();
}

// ------------------------------------------------------------------ telemetría 1 Hz
static void telemetria() {
  if (!P.cx_on) return;
  uint32_t s = hal_rtc_s();
  char hora[12]; snprintf(hora, sizeof hora, "%02lu:%02lu:%02lu", (unsigned long)(s / 3600 % 24),
                          (unsigned long)(s / 60 % 60), (unsigned long)(s % 60));
  char hgps[12]; snprintf(hgps, sizeof hgps, "%02lu:%02lu:%02lu",
                          (unsigned long)(gps.hora_s / 3600 % 24),
                          (unsigned long)(gps.hora_s / 60 % 60), (unsigned long)(gps.hora_s % 60));
  char solar[12] = "";
  if (P.pwr_extra) snprintf(solar, sizeof solar, "%.2f", hal_solar_v());
  P.packet_count++;
  char t[320];
  snprintf(t, sizeof t,
           "%s,%s,%lu,%c,%s,%.1f,%.1f,%.1f,%.1f,%.2f,%.1f,%.1f,%.1f,%.2f,%.2f,%.2f,"
           "%s,%.1f,%.4f,%.4f,%u,%s,,%.0f,%u,%s\r",
           TEAM_ID, hora, (unsigned long)P.packet_count, P.modo_sim == 2 ? 'S' : 'F',
           NOMBRE[P.estado], kf.h, temp_c, p_ult / 1000.0f, hal_vbat(), hal_ibat(),
           gyr[0], gyr[1], gyr[2], acc[0], acc[1], acc[2], hgps, gps.alt, gps.lat, gps.lon,
           gps.sats, eco, rpm_f, P.latch, solar);
  hal_radio_send(t);
  hal_sd_log(t);
  persist_guardar();                                       // F1: contador persistente
}

// ------------------------------------------------------------------ arranque y lazo
static uint32_t t_ctrl = 0, t_tlm = 0, t_ult_ctrl = 0;

void setup() {
  hal_servo_power(false);                       // primero la posición, después la energía
  bool ok = persist_cargar();
  if (!ok) { memset(&P, 0, sizeof P); P.p0 = 101325.0f; P.estado = LAUNCH_PAD; }
  hal_servo_us(P.latch ? SERVO_LIBRE_US : SERVO_TRABA_US);
  hal_servo_power(true);
  float p = hal_baro_pa();
  kf.init(isnan(p) ? P.h_ult : altura_isa(p, P.p0));
  hmax_corrida = P.h_max;
  switch (P.estado) {                           // recuperación tras un reinicio (tabla)
    case ASCENT:  t_desp = -(T_BLOQUEO - 2.0f); hal_cam_power(true); break;
    case APOGEE:
    case DESCENT: {
      P.estado = DESCENT;
      int32_t d = (int32_t)hal_rtc_s() - (int32_t)P.t_apogeo_s;
      if (d < 0) d += 86400;
      t_apo = -(float)d; t_desp = t_apo - 10.0f; hal_cam_power(true); break;
    }
    case PROBE_RELEASE: traba(true); t_lib = 0; hal_cam_power(true); break;
    case PAYLOAD_RELEASE: hal_cam_power(true); break;
    default: break;
  }
  hal_hall_attach(isr_hall);
  hal_wdt_begin(1000);                          // perro guardián de 1 s
  t_ctrl = t_tlm = t_ult_ctrl = millis();
}

void loop() {
  uint32_t ahora = millis();
  if (ahora - t_ctrl >= T_CONTROL_MS) {
    t_ctrl += T_CONTROL_MS;
    if (ahora - t_ctrl > 5 * T_CONTROL_MS) t_ctrl = ahora;  // no acumula atraso
    control(T_CONTROL_MS / 1000.0f);
    t_ult_ctrl = ahora;
  }
  if (ahora - t_tlm >= T_TLM_MS) { t_tlm += T_TLM_MS; telemetria(); }
  char linea[64];
  if (hal_radio_line(linea, sizeof linea) > 0) comando(linea);
  if (millis() - t_ult_ctrl < 100) hal_wdt_kick();          // solo si el control corre
}

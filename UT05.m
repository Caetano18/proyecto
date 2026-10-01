% Sistemas de Control - UT05: aeronave en cabeceo con fuselaje flexible
clear; clc; close all;
s = tf('s');

K  = 1;
Ga = 50/(s+50);
Gt = 18*(s+1)/(s*(s^2+4.2*s+9));
Gf = 400/(s^2+s+400);
L  = K*Ga*Gt*Gf;
Lr = K*Ga*Gt;
T  = feedback(L,1);

%% 1. Diagrama de Bode
figure; bode(L); grid on;
Kv = dcgain(minreal(s*L))           % 1.d
t  = 0:0.01:30;
y  = lsim(T,t,t);
ess = t(end) - y(end)               % 1.e

%% 2. Resonancia estructural
zf = 0.025;
Mr = 1/(2*zf*sqrt(1-zf^2))          % 2.a
wr = 20*sqrt(1-2*zf^2)
figure; bode(L,Lr); grid on;        % 2.b
for z = [0.0125 0.02 0.025 0.03 0.05]   % 2.d
    Gz = 400/(s^2+40*z*s+400);
    [pico,~] = getPeakGain(K*Ga*Gt*Gz,1e-4,[15 25]);
    fprintf('zeta = %.4f -> pico = %.2f dB\n', z, 20*log10(pico));
end

%% 3. Margenes y ganancia critica
figure; margin(L);
[Gm,Pm,Wpc,Wgc] = margin(L)
Kc = Gm
polos_Kc = pole(feedback(Kc*Ga*Gt*Gf,1))

%% 4. Estabilidad absoluta y relativa
L2 = K*Ga*Gt*400/(s^2+0.5*s+400);   % zeta = 0.0125
figure; margin(L2);
estable = isstable(feedback(L2,1))
Tj = evalfr(T,1j*19.5);
amplitud = abs(Tj)
fase = angle(Tj)*180/pi

%% 5. Correlacion tiempo-frecuencia
info = stepinfo(T)
figure; step(T, feedback(Lr,1), 10); grid on;

%% Opcional: Nyquist y fase no minima
figure; nyquist(L);
Lnm = K*Ga*Gf*18*(1-s)/(s*(s^2+4.2*s+9));
figure; bode(L,Lnm); grid on;
[GmN,PmN] = margin(Lnm)

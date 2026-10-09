% Respuesta en frecuencia y compensacion - verificacion de los ejemplos del apunte
clear; clc; close all;
s = tf('s');

%% Ejemplo 1: trazado de Bode
G1 = 16000*(s+1)/(s*(s+5)*(s^2+16*s+1600));
figure; bode(G1); grid on;
[Gm,Pm,Wpc,Wgc] = margin(G1)                % MF = 106.4, MG = 1.68 (4.5 dB)

%% Ejemplo 2: Nyquist, margenes y Nichols de K/(s(s+1)(s+2))
G2 = 1/(s*(s+1)*(s+2));
figure; nyquist(2*G2, 8*G2); legend('K = 2','K = 8');
[Kc,~,w180] = margin(G2)                    % Kc = 6 en w = 1.414 rad/s
figure; margin(2*G2);                       % MF = 32.6, MG = 9.54 dB
figure; nichols(2*G2); ngrid;
T2 = feedback(2*G2,1);
Mr_dB = 20*log10(getPeakGain(T2))           % 5.3 dB
wBW = bandwidth(T2)                         % 1.26 rad/s

%% Ejemplo 3: adelanto
G  = 1/(s*(s+1)*(0.05*s+1));
K  = 10;  L0 = K*G;                         % 1. ganancia por Kv
[~,MF0,~,wc0] = margin(L0)                  % MF0 = 9.4 en 3.07 rad/s
phim = 45 - MF0 + 12;                       % 2. delta = 12 (con 5 no alcanza)
alfa = (1-sind(phim))/(1+sind(phim))        % 3. 0.15
wm   = fzero(@(x) magdB(L0,x) + 10*log10(1/alfa), [wc0 100])   % 4. 4.96
T    = 1/(wm*sqrt(alfa));                   % 5.
Gc   = K*(T*s+1)/(alfa*T*s+1)
L    = Gc*G;
[Gm,Pm,Wpc,Wgc] = margin(L)                 % 6. MF = 45.2, MG = 14.9 dB
figure; bode(L0, L, Gc/K); grid on; legend('L_0','L','G_c/K');
figure; step(feedback(L0,1), feedback(L,1), 8); legend('sin comp.','adelanto');

%% Ejemplo 4: atraso
G  = 1/(s*(s+2)*(s+5));
K  = 100; L0 = K*G;                         % inestable: MF0 = -8.9
wt   = fzero(@(x) fase(L0,x) - (-180+45+6), [0.1 3])   % 1.03 rad/s
wcn  = 1;                                   % se redondea hacia abajo
beta = 10^(magdB(L0,wcn)/20)                % 8.77 -> se toma 9
beta = 9;
T    = 10/wcn;
Gc   = K*(T*s+1)/(beta*T*s+1)
L    = Gc*G;
[Gm,Pm,Wpc,Wgc] = margin(L)                 % MF = 47.5, MG = 15.4 dB
Kg = 14.66;                                 % solo ganancia, MF = 45 (Kv = 1.47)
t  = 0:0.01:25;
figure; step(feedback(L,1), feedback(Kg*G,1), 25); legend('atraso','solo ganancia');
figure; lsim(feedback(L,1), feedback(Kg*G,1), t, t); legend('atraso','solo ganancia');

%% Ejemplo 5: atraso-adelanto
G   = 1/(s*(s+1)*(s+4));
K   = 40; L0 = K*G;
[~,~,w180] = margin(L0);                    % 2 rad/s
wcn  = w180;
phim = 50 - (180 + fase(L0,wcn)) + 6;       % 56 grados
alfa = (1-sind(phim))/(1+sind(phim))        % 0.0935
T1   = 1/(wcn*sqrt(alfa));
Glead = (T1*s+1)/(alfa*T1*s+1);
A    = magdB(L0*Glead, wcn)                 % 16.3 dB
beta = 10^(A/20)                            % 6.54
T2   = 10/wcn;
Glag = (T2*s+1)/(beta*T2*s+1);
Gc   = K*Glead*Glag
L    = Gc*G;
[Gm,Pm,Wpc,Wgc] = margin(L)                 % MF = 51.0, MG = 13.3 dB
figure; bode(L0, L); grid on; legend('L_0','L');
figure; step(feedback(L,1), 20);

%% Comparacion adelanto vs atraso sobre 1/(s(s+1)), Kv = 10
G   = 1/(s*(s+1));
Lad = 10*(s/2.321+1)/(s/7.566+1)*G;
Lat = 10*(s/0.081+1)/(s/0.00844+1)*G;
[~,PmAd,~,WgcAd] = margin(Lad)              % 45.5 grados en 4.19 rad/s
[~,PmAt,~,WgcAt] = margin(Lat)              % 45.8 grados en 0.81 rad/s
figure; step(feedback(10*G,1), feedback(Lad,1), feedback(Lat,1), 15);
legend('solo K','adelanto','atraso');

%% Ejercicio 15: aeronave de la UT05
Ga  = 50/(s+50); Gt = 18*(s+1)/(s*(s^2+4.2*s+9)); Gf = 400/(s^2+s+400);
Gav = Ga*Gt*Gf;
L0  = 2*Gav;
allmargin(L0)
pico_dB = 20*log10(getPeakGain(L0,1e-4,[15 25]))         % +4.5 dB
Llead = L0*(s/4.99+1)/(s/15.7+1);
polos_adelanto = pole(feedback(Llead,1))                 % +0.61 +- j17.4: inestable
Llag  = L0*(4*s+1)/(14.48*s+1);
[Gm,Pm,Wpc,Wgc] = margin(Llag)                           % MF = 75.1, MG = 19.2 dB
pico_atraso_dB = 20*log10(getPeakGain(Llag,1e-4,[15 25]))  % -6.7 dB
figure; bode(Gav, L0, Llead, Llag, {0.1 100}); grid on;
legend('K = 1','K = 2','K = 2 + adelanto','K = 2 + atraso');

%% Funciones auxiliares
function m = magdB(L,w)
m = 20*log10(abs(evalfr(L,1j*w)));
end

function f = fase(L,w)
% fase desenrollada desde baja frecuencia (evita saltos de +-360)
ww = logspace(-4, log10(w), 2000);
[~,ph] = bode(L, ww);
f = ph(end);
end

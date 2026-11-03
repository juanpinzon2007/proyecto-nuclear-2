-- Una nota almacenada ficticia para comprobar conservación, NO cálculo académico.
BEGIN;
INSERT INTO consentimiento VALUES (501,12,'texto-lab','2030-01-01',NULL);
INSERT INTO participacion VALUES (601,401,110,'ensayo','2030-01-02 09:00:00');
INSERT INTO intento VALUES (701,601,501,NULL,1,'FINALIZADO','2030-01-02 09:00:00','2030-01-02 09:05:00');
INSERT INTO paso_simulacion VALUES (801,701,201,301,1,'2030-01-02 09:01:00',60,NULL);
INSERT INTO resultado_intento VALUES (901,701,3.25,'2030-01-02 09:05:00','Nota sintética, no fórmula aprobada');
INSERT INTO resultado_criterio VALUES (911,901,21,32,1.95),(912,901,22,34,1.30);
INSERT INTO resultado_participacion VALUES (921,601,'ensayo',3.25,'2030-01-02 09:05:00','No es calificación oficial');
COMMIT;

# La Stella di Valdimora — design

Data: 2026-09-29. Approvato in chat sezione per sezione; questo documento lo mette per iscritto.

## Obiettivo

Una terza avventura, **per adulti**, molto più grande della Rocca: un giallo in un castello abitato,
con enigmi intrecciati, una trama da scoprire e qualche pericolo. La Rocca resta l'esempio piccolo,
il draghetto l'avventura per bambini.

Cosa ha deciso l'utente:

- **Giallo**, con **enigmi intrecciati** (più fili aperti insieme) e **una trama da scoprire**
  (personaggi con segreti), più **un po' di pericoli** (morti e finali diversi).
- **50 stanze in 4 zone, una zona per piano, un atto per zona**; **30-35 enigmi**; **4-5
  personaggi**.
- **Strada A**: tutta la trama progettata prima (questo documento), poi costruita **un atto alla
  volta**, ciascuno con il suo branch e la sua PR, giocabile fino a un finale provvisorio.
- La storia: **la caccia della contessa**. La contessa ha nascosto una cosa preziosa che voleva
  trovasse la protagonista, in fondo a una pista di enigmi; non un testamento.
- La protagonista **è una donna** e **scopre chi è durante il gioco**, un pezzo per atto.
- **Autunno 1927.**
- Colpevole: **Agnese**, amante segreta di **Corrado**, che non sa niente del delitto.
- **Tre finali**: completo, a metà, tradita.
- Due aggiunte al motore, **senza toccare il prompt dell'LLM**: personaggi che si spostano, e
  salvataggio automatico all'inizio di ogni atto (dopo una morte si riprende da lì).

Criterio di riuscita: dal menu si sceglie «La Stella di Valdimora» e la si gioca dall'arrivo a uno
dei tre finali, anche con frasi libere; la Rocca e il draghetto si giocano come prima
(`tests/test_ollama.py` verde, a parte i limiti noti); una morte non costa più di un atto.

## Scomposizione

| # | Branch | Contenuto |
|---|---|---|
| 1 | `feature/inizia_l_Avventura` | questa specifica; poi il motore (sezione 5) e `docs/formato-mondo.md` |
| 2 | `feature/valdimora-atto-1` | pianterreno: dati, testi, test; nel menu con un finale provvisorio |
| 3 | `feature/valdimora-atto-2` | piano nobile |
| 4 | `feature/valdimora-atto-3` | soffitta |
| 5 | `feature/valdimora-atto-4` | cantina, i tre finali; via il finale provvisorio |

Ogni pezzo ha il suo piano dettagliato, scritto quando si comincia.

---

## 1. La storia

### Nomi

| Chi | Nome | Note |
|---|---|---|
| La protagonista | **Irene** | 29 anni, sarta a Genova come la madre; i testi le si rivolgono al femminile |
| Sua madre | **Clara** | nata nel 1878 a Valdimora, morta di spagnola nel 1918 |
| La contessa | **Adelaide di Valdimora** | 72 anni, malata di cuore; morta il 14 ottobre 1927 |
| Il conte | **Ruggero di Valdimora** | morto nel 1915 |
| Il castello | **Valdimora** | in una valle di montagna; una sola strada |

Titolo per il menu: **La Stella di Valdimora**. Id dell'avventura: `valdimora`.

### Antefatto

- **1878.** Nasce Clara, figlia di Adelaide e Ruggero. Il conte fa mettere in cantina una botte
  con l'anno di nascita della figlia.
- **1897.** Clara, diciannovenne, resta incinta. **Livia**, allora giovane cameriera, lo rivela al
  conte, che la caccia di casa. **Ettore** la aiuta a fuggire di notte; per anni le manda di
  nascosto notizie e qualche soldo. Il conte fa coprire il ritratto di Clara nella galleria.
- **1898.** A Genova nasce **Irene**. Clara fa la sarta e non le parla mai di Valdimora; le lascia
  solo un **medaglione** d'argento con una stella incisa, che portava da ragazza.
- **1915.** Muore il conte. **Corrado**, figlio del fratello minore del conte, si considera
  l'erede di tutto.
- **1918.** Clara muore di spagnola. Ettore lo viene a sapere e tace.
- **Primavera 1927.** La contessa, malata, chiede a Ettore la verità su Clara e scopre che esiste
  una nipote. Vuole riconoscerla davanti al notaio come nipote ed erede, e vuole che la **Stella di
  Valdimora** — il gioiello che nella sua famiglia passa di madre in figlia da cinque generazioni,
  e che non è dei conti — arrivi a lei.
- **Giugno.** La contessa scrive a Irene; le lettere le spedisce **Agnese**, la dama di compagnia,
  che le legge e le trattiene. Agnese è da un anno l'amante segreta di Corrado, che le ha promesso
  di sposarla quando erediterà: una nipote di sangue gli toglierebbe tutto, e a lei il futuro da
  contessa.
- **Estate.** La contessa si accorge che le sue lettere non partono. Nasconde in cantina la Stella
  e **le prove di chi è Irene** (le lettere di Clara, una sua dichiarazione firmata, l'atto di
  nascita), e costruisce una **pista di enigmi** — la sua passione di sempre — che si segue solo
  con il medaglione di Clara. Fissa col notaio il riconoscimento per il 20 ottobre.
- **Inizio ottobre.** Affida a Ettore l'ultima lettera per Irene, vaga di proposito («Ho una cosa
  che appartiene a voi e a vostra madre. Venite a Valdimora, vi spiegherò ogni cosa»), e il primo
  indizio, da consegnare solo «alla ragazza con la lettera».
- **14 ottobre.** Agnese, capito che la contessa non le dirà niente e che la nipote sta arrivando,
  le dà una dose eccessiva del suo farmaco per il cuore (digitale, in gocce), e nasconde il
  flacone. Il **dottor Ferri** firma «arresto cardiaco»: Corrado, che non sa niente del delitto, lo
  ha spinto a fare in fretta per evitare giornali e domande (Ferri gli deve dei soldi persi al
  gioco). Agnese cerca la Stella da sola, senza riuscirci.
- **17 ottobre.** Arriva Irene, con la lettera e il medaglione. Dietro la sua corriera una frana
  chiude la strada: nessuno può lasciare Valdimora, e il notaio non può arrivare. La contessa
  riposa nella cappella, in attesa che la strada riapra. Agnese la accoglie con un sorriso: le
  serve che la pista la risolva lei.

### Personaggi

| Chi | Chi è | Segreto | Nella storia |
|---|---|---|---|
| **Ettore**, maggiordomo, 70 anni | a Valdimora da cinquant'anni, ha visto nascere Clara | aiutò Clara a fuggire e le scrisse per anni | custodisce il primo indizio; garantisce per Irene |
| **Livia**, governante, 48 anni | fredda, tiene tutte le chiavi | nel 1897 rivelò al conte la gravidanza di Clara | chiude lo scalone; confessa nell'atto 3 |
| **Corrado**, nipote del conte, 40 anni | sgarbato, pieno di debiti | vuole tutta l'eredità; ha spinto Ferri a firmare in fretta | falsa pista; quando scopre chi è Irene le diventa nemico; nel finale completo ferma Agnese |
| **Il dottor Ferri**, 60 anni | medico di famiglia, beve | deve soldi a Corrado | ha la chiavetta dell'armadietto dei medicinali; spinge i sospetti su Corrado |
| **Agnese**, dama di compagnia, 30 anni | dolce, la prima ad aiutare | legge le lettere altrui; amante di Corrado; ha ucciso la contessa | aiuta Irene per tutto il gioco, si rivela in cantina |

Nessuno, tranne Agnese e i finali, cambia la partita con un effetto che accorci la pista: i
personaggi danno indizi, chiavi previste dagli enigmi e informazioni.

### Cosa sa Irene, e cosa scopre

All'inizio sa che la madre si chiamava Clara, faceva la sarta ed è morta nel 1918, che non le ha
mai parlato della sua famiglia, e che le ha lasciato il medaglione. Poi, un piano alla volta:

| Atto | Rivelazione |
|---|---|
| 1 | Ettore vede il medaglione: «Avete gli occhi di vostra madre.» Clara è stata a Valdimora. |
| 2 | Il ritratto coperto della galleria: Clara a vent'anni, col medaglione al collo. Era della famiglia. |
| 3 | Le lettere mai spedite «a mia figlia Clara»: la contessa era sua nonna. Subito dopo lo scopre anche Corrado. |
| 4 | La Stella, le prove di chi è, e chi ha ucciso la contessa. |

---

## 2. Gli atti

Ogni atto apre un piano. Gli atti si susseguono, ma **i piani già aperti restano aperti**: diversi
enigmi chiedono di tornare su e giù. Il salvataggio automatico scatta all'inizio di ogni atto
(sezione 5).

| Atto | Piano | Si apre con | Obiettivo | Prova del delitto (facoltativa) | Pericoli |
|---|---|---|---|---|---|
| 1 | pianterreno (piano terra) | l'arrivo | la chiave dello scalone | il registro delle medicine | nessuno |
| 2 | piano nobile (primo piano) | la porta dello scalone | la chiave della scala di servizio | il flacone vuoto | il balcone |
| 3 | soffitta (secondo piano) | la porta della scala di servizio | la chiave della cantina e la lanterna accesa | la lettera intercettata | il sottotetto, il tetto |
| 4 | cantina (piano -1) | la porta della cantina, in cucina | la Stella, e uscire | — | la ghiacciaia, lo scaffale; Agnese |

Dove sono i personaggi (con `moves`, sezione 5):

| | Atto 1 | Atto 2 | Atto 3 | Atto 4 |
|---|---|---|---|---|
| Ettore | Stanza del maggiordomo | Galleria dei ritratti | Cucina | Cucina |
| Livia | Ufficio della governante | Camera della contessa | Camera di Livia | Cucina |
| Corrado | Sala del biliardo | Studio del conte | Archivio di famiglia | Cucina |
| Ferri | Sala del biliardo | Biblioteca | Salotto | Salotto |
| Agnese | Cappella | Loggia dello scalone | Corridoio della servitù (in Rimessa o in Cucina durante le commissioni) | Scala della cantina («Vi aspetto qui»); Cantina dei vini quando si rivela |

---

## 3. La piantina

Un quadrilatero intorno al cortile, con l'ingresso a sud; i piani superiori seguono lo stesso
perimetro. 50 stanze: 13 + 13 + 12 + 12. Le uscite sono a senso unico nel formato, quindi ognuna è
scritta nelle due stanze; qui le elenco una volta per coppia. Le descrizioni nomineranno le stanze
vicine col loro nome, perché «vai in biblioteca» funzioni senza LLM.

### Collegamenti tra i piani

| Collegamento | Da (su/giù) | Chiuso finché |
|---|---|---|
| Scalone | Atrio `su` ↔ Loggia dello scalone `giù` | la porta dello scalone non è aperta con la chiave di Livia |
| Scala di servizio | Pianerottolo di servizio `su` ↔ Pianerottolo della soffitta `giù` | la porta non è aperta con la chiave del carillon |
| Scala della cantina | Cucina `giù` → Scala della cantina | la porta non è aperta con la chiave della casa delle bambole **e** la lanterna non è accesa; dalla Scala della cantina `su` è chiusa per sempre («La porta è chiusa dall'altra parte») |
| Scivolo della carbonaia | Carbonaia `su` → Cortile | la scala a pioli non è appoggiata e il lucchetto della grata non è aperto; dal Cortile non si scende |

### Piano terra: pianterreno (13)

| Stanza (id) | Uscite | Cosa c'è |
|---|---|---|
| Atrio (`atrio`) — **partenza** | n Cortile, s Rimessa, o Salotto, e Sala del biliardo, su Loggia | la porta dello scalone |
| Rimessa (`rimessa`) | n Atrio | la valigia, l'oliatore, le forbici da potatura, la tanica di petrolio |
| Salotto (`salotto`) | e Atrio, n Sala da pranzo, o Serra | |
| Serra (`serra`) | e Salotto | il rosaio delle rose bianche |
| Sala da pranzo (`sala_da_pranzo`) | s Salotto, e Cortile, n Stanza del maggiordomo | la credenza (la grappa) |
| Stanza del maggiordomo (`stanza_maggiordomo`) | s Sala da pranzo, e Cucina | |
| Cucina (`cucina`) | o Stanza del maggiordomo, s Cortile, e Dispensa, n Lavanderia, giù Scala della cantina | la porta della cantina, i fiammiferi |
| Lavanderia (`lavanderia`) | s Cucina | |
| Dispensa (`dispensa`) | o Cucina, e Ufficio della governante | l'armadietto dei medicinali (il registro) |
| Ufficio della governante (`ufficio_governante`) | o Dispensa, s Cappella | |
| Cappella (`cappella`) | n Ufficio della governante, o Cortile, s Sala del biliardo | la bara della contessa |
| Sala del biliardo (`biliardo`) | n Cappella, o Atrio | la borsa del dottore |
| Cortile (`cortile`) | s Atrio, n Cucina, o Sala da pranzo, e Cappella | la meridiana, la grata della carbonaia |

### Primo piano: piano nobile (13)

| Stanza (id) | Uscite | Cosa c'è |
|---|---|---|
| Loggia dello scalone (`loggia`) | giù Atrio, n Galleria, o Salone delle feste, e Salone della musica | |
| Salone delle feste (`salone_feste`) | e Loggia, s Balcone, n Salottino verde | |
| Balcone (`balcone`) | n Salone delle feste | la balaustra crepata, il vaso di gerani (il flacone) |
| Salottino verde (`salottino_verde`) | s Salone delle feste, n Camera della contessa, e Galleria | |
| Camera della contessa (`camera_contessa`) | s Salottino verde, o Boudoir, e Guardaroba | |
| Boudoir (`boudoir`) | e Camera della contessa — chiuso finché Livia non lo permette | il portagioie (la chiavetta di carica) |
| Guardaroba (`guardaroba`) | o Camera della contessa, e Pianerottolo di servizio | |
| Galleria dei ritratti (`galleria`) | s Loggia, o Salottino verde, e Biblioteca, n Pianerottolo di servizio | il ritratto coperto di Clara |
| Pianerottolo di servizio (`pianerottolo_servizio`) | s Galleria, o Guardaroba, su Pianerottolo della soffitta | la porta della scala di servizio |
| Salone della musica (`salone_musica`) | o Loggia, n Biblioteca | il carillon |
| Biblioteca (`biblioteca`) | s Salone della musica, o Galleria, n Studio del conte | |
| Studio del conte (`studio_conte`) | s Biblioteca, n Camera di Corrado | il bastone col manico ricurvo |
| Camera di Corrado (`camera_corrado`) | s Studio del conte | |

### Secondo piano: soffitta (12)

| Stanza (id) | Uscite | Cosa c'è |
|---|---|---|
| Pianerottolo della soffitta (`pianerottolo_soffitta`) | giù Pianerottolo di servizio, o Corridoio della servitù, e Soffittone, n Stenditoio | |
| Stenditoio (`stenditoio`) | s Pianerottolo della soffitta | l'asse lunga, la corda da bucato |
| Corridoio della servitù (`corridoio_servitu`) | e Pianerottolo, n Camera di Agnese, s Camera di Livia, o Camera di Clara | |
| Camera di Agnese (`camera_agnese`) | s Corridoio — si entra solo mentre Agnese è in commissione | lettera intercettata, anello, quaderno |
| Camera di Livia (`camera_livia`) | n Corridoio | |
| Camera di Clara (`camera_clara`) | e Corridoio — chiusa dal 1897 | il baule delle lettere, la casa delle bambole |
| Soffittone (`soffittone`) | o Pianerottolo, n Sottotetto, e Archivio, s Stanza dell'orologio | il pavimento marcio (visto da qui) |
| Sottotetto (`sottotetto`) | s Soffittone | la lanterna |
| Archivio di famiglia (`archivio`) | o Soffittone | le carte del conte del 1897 |
| Stanza dell'orologio (`stanza_orologio`) | n Soffittone, su Tetto | il meccanismo, il lucernario |
| Tetto (`tetto`) | giù Stanza dell'orologio, e Piccionaia | la tempesta |
| Piccionaia (`piccionaia`) | o Tetto | il piccione col tubetto (la lettera del notaio) |

### Piano -1: cantina (12)

| Stanza (id) | Uscite | Cosa c'è |
|---|---|---|
| Scala della cantina (`scala_cantina`) | su Cucina (chiusa), s Corridoio delle volte | |
| Corridoio delle volte (`corridoio_volte`) | n Scala, o Vecchia cucina, e Cantina dei vini, s Magazzino delle conserve | |
| Vecchia cucina (`vecchia_cucina`) | e Corridoio, n Lavatoio, s Legnaia | il coltello |
| Lavatoio (`lavatoio`) | s Vecchia cucina, n Cisterna | |
| Cisterna (`cisterna`) | s Lavatoio | |
| Legnaia (`legnaia`) | n Vecchia cucina, e Magazzino | i ceppi, la scala a pioli |
| Magazzino delle conserve (`magazzino`) | n Corridoio, o Legnaia, e Carbonaia | |
| Carbonaia (`carbonaia`) | o Magazzino, su Cortile (chiusa) | lo scivolo, la grata col lucchetto |
| Cantina dei vini (`cantina_vini`) | o Corridoio, e Bottiglieria, n Stanza segreta (chiusa) | le tre botti, lo scaffale pericolante |
| Bottiglieria (`bottiglieria`) | o Cantina dei vini, s Ghiacciaia | la porta della ghiacciaia |
| Ghiacciaia (`ghiacciaia`) | n Bottiglieria | la chiave del lucchetto |
| Stanza segreta (`stanza_segreta`) | s Cantina dei vini | la cassetta (la Stella, le prove) |

Rispetto alla piantina discussa in chat, lo scaffale pericolante sta nella **cantina dei vini**
(dove Agnese si rivela), non nella bottiglieria; la cisterna non è un pericolo.

---

## 4. Gli enigmi

35 enigmi: 9 + 9 + 9 + 8. Nessuna combinazione numerica e nessuna parola da digitare: tutto si
risolve con i verbi che il motore ha già (esamina, prendi, lascia, usa X con Y, apri, chiudi,
spingi, tira, leggi, dai, parla, chiedi), e le frasi libere ci arrivano attraverso l'interprete.
Tra parentesi, come si scrive nei dati; i nomi dei flag sono indicativi.

### Atto 1: pianterreno

```
 Rimessa: valigia ──> fotografia di Clara ───────────────────────────> (atto 2, atto 3)
 Rimessa: oliatore ─────────────────────┐
                                        v
 lettera ─> Ettore ─> busta ─> indovinello ─> meridiana ─> biglietto sigillato «Per Livia»
            (rivelazione 1)                 (olio + medaglione)      │
                                                                     v
                            Livia dubita ─> Ettore garantisce ─> Livia dà la chiave ─> scalone ─> ATTO 2

 facoltativo: Ettore ─> chiave della credenza ─> grappa ─> Ferri si appisola ─> la sua borsa
              ─> chiavetta ─> armadietto in dispensa ─> registro delle medicine (PROVA 1)
```

1. **La valigia** — `apri valigia` (Rimessa) dà la fotografia di Clara.
2. **Ettore** — `dai lettera a Ettore`: la legge, vede il medaglione (rivelazione 1) e dà la busta
   della contessa. La lettera resta a Irene.
3. **L'indovinello** — `leggi busta`: «Conto le ore solo col sole; quando piove, cercami più in
   basso.» (flag `busta_letta`). Da allora la meridiana, esaminata, mostra alla base un incavo a
   stella (variante della descrizione).
4. **La ruggine** — `usa oliatore con meridiana` (flag `meridiana_oliata`); poi `usa medaglione
   con meridiana` apre lo scomparto: il biglietto sigillato «Per Livia» e l'indizio «Cerca chi ti
   somiglia». Prima dell'olio: «Il medaglione entra nell'incavo ma non gira»; dopo averlo aperto:
   «Lo scomparto è vuoto» (`otherwise_variants`).
5. **Livia dubita** — `dai biglietto a Livia` senza la garanzia di Ettore: «È la sua scrittura. Ma
   una lettera si ruba. Chi garantisce per voi?» (una regola sola: `when` sulla garanzia,
   `otherwise` il dubbio).
6. **Ettore garantisce** — `chiedi a Ettore di Livia` (argomento sempre disponibile; effetto
   `ettore_garantisce`).
7. **Lo scalone** — `dai biglietto a Livia` con la garanzia dà la chiave dello scalone; `apri porta
   dello scalone con chiave` apre l'uscita e attiva `atto_due`.
8. **Il dottore** (facoltativo) — Ferri non lascia toccare la borsa. `chiedi a Ettore della
   credenza` dà la chiave della credenza; `apri credenza con chiave` dà la grappa; `dai grappa a
   Ferri`: beve e si appisola (flag, variante del saluto). Ora `prendi borsa`/`esamina borsa` dà la
   chiavetta dell'armadietto.
9. **L'armadietto** (facoltativo) — `apri armadietto con chiavetta` (Dispensa) dà il registro:
   nell'ultima settimana le gocce raddoppiate, ogni riga siglata «A.» — che il giocatore crederà
   Adelaide. **Prova 1.**

Nessun pericolo. Corrado è sgarbato e lascia capire che conta sull'eredità.

### Atto 2: piano nobile

```
 «Cerca chi ti somiglia» ─> Galleria: ritratto coperto ─> Clara (+ fotografia: rivelazione 2)
                                     │
                          medaglione nella cornice ─> cilindro del carillon ──────┐
                                                                                   v
 Serra (si torna giù) ─> rosa bianca ─> Livia ─> boudoir ─> chiavetta di carica
                                                                                   │
                                                  Salone della musica: carillon <──┘
                                                  la ninna nanna ─> chiave della scala di servizio ─> ATTO 3

 facoltativo: Studio del conte: bastone ─> Balcone: vaso in bilico ─> flacone (PROVA 2)
```

1. **Il ritratto coperto** — `prendi drappo` (Galleria) scopre il ritratto. Esaminato con la
   fotografia in mano: «È lei. È tua madre.» (rivelazione 2, variante con `has: fotografia`).
2. **La cornice** — `usa medaglione con ritratto` dà il cilindro del carillon e il biglietto
   «Suonala per me, come faceva lei».
3. **La rosa bianca** — Livia ricorda la rosa bianca sul comodino della contessa (argomento).
   `usa forbici con rosaio` (Serra, al pianterreno; forbici nella Rimessa) dà la rosa.
4. **Livia cede** — `dai rosa a Livia` (flag `livia_permette`): si apre l'uscita verso il Boudoir.
5. **Il portagioie** — `apri portagioie` (Boudoir) dà la chiavetta di carica.
6. **Il carillon** — `usa cilindro con carillon`, poi `usa chiavetta con carillon`: la ninna nanna
   di Clara; la base si apre e dà la chiave della scala di servizio e l'indizio «Dove lei dormiva
   bambina».
7. **La scala di servizio** — `apri porta di servizio con chiave` apre l'uscita e attiva
   `atto_tre`.
8. **Il bastone** (facoltativo) — Corrado nello studio: «Prendete quello che volete.» `prendi
   bastone`.
9. **Il vaso** (facoltativo) — `usa bastone con vaso` (Balcone) dà il flacone vuoto: **prova 2**.
   **Pericolo:** `prendi vaso`, `spingi balaustra`, `salta balaustra` fanno crollare la balaustra
   (flag, finale di morte). La descrizione del balcone lo avverte.

Indizi senza enigma: Ferri, in biblioteca, sulla morte della contessa («Corrado insisteva per non
chiamare nessuno da fuori»: falsa pista); Agnese chiede di vedere il medaglione — `dai medaglione
ad Agnese` negli atti 1-3 non ha effetti: lo rigira e lo rende, «Che strana stella» (è l'`otherwise`
della regola che nell'atto 4 porta al finale «tradita»).

### Atto 3: soffitta

```
 fotografia ─> Livia confessa (1897) ─> chiave della camera di Clara
                                              │
          Camera di Clara: lettere «a mia figlia Clara» (RIVELAZIONE 3) ─> Corrado lo scopre (svolta)
                          casa delle bambole + medaglione ─> chiave della cantina ────────┐
                                                                                          v
 Stenditoio: asse ─> pavimento marcio ─> Sottotetto: lanterna ─┐                   Cucina: porta
 petrolio (Rimessa, due piani più giù) ────────────────────────┼─> lanterna accesa ─> della cantina ─> ATTO 4
 fiammiferi (Cucina) ──────────────────────────────────────────┘

 facoltativo: chiedi ad Agnese il petrolio ─> lei scende in Rimessa ─> la sua stanza è libera
              ─> lettera intercettata + anello «C. ad A.» + quaderno (PROVA 3)
 facoltativo: Stenditoio: corda ─> lucernario ─> Tetto ─> Piccionaia: lettera del notaio (il movente)
```

1. **Livia confessa** — `dai fotografia a Livia`: racconta il 1897 e dà la chiave della camera di
   Clara (la fotografia torna a Irene).
2. **Le lettere** — `apri porta della camera di Clara con chiave`; nel baule, `leggi lettere`:
   **rivelazione 3** (flag `lettere_lette`). Da quel momento Corrado, nell'archivio, la affronta:
   «Allora siete voi. La nipotina.» (varianti del saluto e della stanza).
3. **La casa delle bambole** — `usa medaglione con casa delle bambole` dà la chiave della cantina e
   l'ultimo biglietto: «Dove il vino dorme più vecchio. Quando scenderai, porta con te tutto ciò
   che hai scoperto.»
4. **Il pavimento marcio** — `usa asse con pavimento` (dal Soffittone). **Pericolo:** entrare nel
   Sottotetto senza l'asse è un finale di morte (`{all: [{player_in: sottotetto}, {not: {flag:
   asse_posata}}]}`). La descrizione del Soffittone lo avverte.
5. **La lanterna** — `prendi lanterna` (Sottotetto), vuota.
6. **Il petrolio** — la tanica è nella Rimessa: `usa tanica con lanterna`.
7. **Accenderla** — `usa fiammiferi con lanterna` (fiammiferi in Cucina): flag `lanterna_accesa`.
   Senza petrolio: «Lo stoppino non prende.»
8. **La stanza di Agnese** (facoltativo) — Agnese sta nel corridoio e si offre: «Se vi serve
   qualcosa di sotto, chiedete a me.» Due commissioni la allontanano (flag, `moves`):
   - `chiedi ad Agnese del petrolio`, finché Irene non ha la tanica: scende in Rimessa; lì,
     chiedendole di nuovo, dà la tanica e torna su;
   - `chiedi ad Agnese di una tisana` (anche «tè», «qualcosa di caldo»), sempre disponibile:
     scende in Cucina; lì dà una tisana — innocua: Agnese ha bisogno di Irene viva — e torna su.

   Mentre è via, l'uscita verso la sua camera è aperta: sotto il materasso la lettera di giugno
   intercettata, l'anello «C. ad A.», il quaderno con la calligrafia del registro. **Prova 3** (la
   lettera). Con la tisana sempre disponibile, la prova non si perde mai.
9. **Il tetto** (facoltativo) — `usa corda con lucernario` (Stanza dell'orologio), poi su, fino
   alla Piccionaia: `prendi tubetto` dà la lettera del notaio, «Vi attendo il 20 per il
   riconoscimento di vostra nipote». **Pericolo:** salire sul Tetto senza la corda legata è un
   finale di morte.

### Atto 4: cantina

`apri porta della cantina con chiave` (Cucina) apre la porta e attiva `atto_quattro`; il testo
riporta l'avvertimento di Ettore, «Siete sicura di avere tutto, signorina?». Si scende solo con la
lanterna accesa. Appena giù, la porta si chiude dall'altra parte: è Corrado. Agnese è scesa con
Irene: «Non abbiate paura, ci sono io.»

```
 «Dove il vino dorme più vecchio» ─> Cantina dei vini: botte del 1878
      crosta ─> coltello (Vecchia cucina) ─> medaglione ─> la botte si apre
      ─> Stanza segreta: cassetta + medaglione ─> la STELLA e le prove di chi è Irene
                                                                          │
                                     Agnese si rivela, sbarra la strada <─┘
                                     spingi lo scaffale ─> lei resta bloccata
                                                                          │
 Legnaia: ceppo ─> Ghiacciaia (bloccane la porta) ─> chiave del lucchetto ┤
 Legnaia: scala a pioli ─> Carbonaia: lo scivolo ─────────────────────────┴─> Cortile: FINALE
```

1. **La botte più vecchia** — tre botti: 1902, 1878, 1921. Quella del 1878 ha un incavo a stella
   sotto la cannella, coperto dal tartaro.
2. **La crosta** — `usa coltello con botte` (coltello nella Vecchia cucina).
3. **La botte si apre** — `usa medaglione con botte`: si apre l'uscita verso la Stanza segreta.
4. **La cassetta** — `usa medaglione con cassetta`: la Stella di Valdimora e le prove di chi è
   Irene (flag `agnese_rivelata`: Agnese si sposta nella Cantina dei vini).
5. **La ghiacciaia** — `usa ceppo con porta della ghiacciaia` (Bottiglieria; ceppo nella Legnaia).
   **Pericolo:** entrare nella Ghiacciaia senza il ceppo è un finale di morte. Dentro, la chiave
   del lucchetto.
6. **Lo scivolo** — `usa scala con scivolo` (scala a pioli nella Legnaia) e `apri lucchetto con
   chiave`: si apre l'uscita verso il Cortile.
7. **Agnese si rivela** — nella Cantina dei vini, col coltello del pane: «Datemi la Stella e quelle
   carte, Irene.» Finché lo scaffale sta in piedi, tutte le uscite della Cantina dei vini tranne
   quella verso la Stanza segreta sono chiuse («Agnese ti sbarra la strada»).
8. **Lo scaffale** — `spingi scaffale`: crolla tra Irene e Agnese (flag `scaffale_crollato`), le
   uscite si riaprono. Prima che Agnese si riveli: «Meglio di no, sta in piedi per miracolo.»
   **Pericolo:** `prendi bottiglia` dallo scaffale, in qualunque momento, lo fa crollare addosso a
   Irene (finale di morte).

Le due metà (la Stella e la via d'uscita) si risolvono nell'ordine che si vuole. Il medaglione non
si può lasciare in nessun atto («È tutto ciò che ti resta di tua madre»), e in cantina neanche la
lanterna.

### I finali

In quest'ordine in `game.endings` (vale il primo che si avvera):

| Finale | Condizione | `death` |
|---|---|---|
| **Tradita** | `dai` ad Agnese, nell'atto 4, la Stella, le prove o il medaglione (flag `tradita`): sorride, chiude Irene nella stanza segreta e porta via la lanterna | sì |
| Morti: balcone, sottotetto, tetto, ghiacciaia, scaffale | i flag e le condizioni degli enigmi sopra | sì |
| **Completo, col movente** | Irene nel Cortile con la Stella, le tre prove e la lettera del notaio | no |
| **Completo** | Irene nel Cortile con la Stella e le tre prove (registro, flacone, lettera intercettata) | no |
| **A metà** | Irene nel Cortile con la Stella | no |
| provvisorio (atti 1-3) | l'atto successivo comincia: «Fine del primo atto. Continua…» | no |

- **Completo**: davanti a tutti, le prove in fila; Corrado capisce cosa ha coperto e trascina fuori
  Agnese. La Stella è di Irene, e il suo nome anche. La variante col movente racconta anche il
  riconoscimento fissato per il 20.
- **A metà**: quando scendono, dietro lo scaffale non c'è nessuno; Agnese è sparita nella notte,
  oltre la frana. La Stella è di Irene, il dubbio resta a Valdimora.
- Contro il vicolo cieco (le prove restano di sopra una volta chiusa la porta): l'ultimo biglietto
  della casa delle bambole e l'avvertimento di Ettore sulla porta della cantina.

---

## 5. Il motore

Tre aggiunte nel primo branch. **Nessuna tocca il prompt dell'LLM** né il parser: niente verbi
nuovi. La Rocca e il draghetto funzionano come oggi.

### 5.1 Personaggi che si spostano

```yaml
agnese:
  location: cappella
  moves:                       # facoltativo; vale il primo la cui condizione è vera
    - when: {flag: agnese_rivelata}
      room: cantina_vini
    - when: {flag: atto_due}
      room: loggia
```

- Modello: `Character.moves: tuple[Move, ...] = ()`, con `Move(when: Condition, room: Id)`.
- `Engine.character_room(character, state)`: la stanza del primo `move` la cui condizione vale,
  altrimenti `location`. `characters_here` la usa, e da lì passano già la descrizione della stanza,
  il parser, i dialoghi, `dai` e l'elenco dei personaggi per l'interprete.
- Validazione: le stanze dei `moves` esistono; le condizioni si controllano come le altre (flag
  letti che nessuno attiva, oggetti e stanze citati).

### 5.2 Atti e salvataggio automatico

```yaml
game:
  acts:                        # facoltativo
    - name: secondo atto       # per «Riprendi dall'inizio del secondo atto»
      when: {flag: atto_due}
  endings:
    - when: {flag: caduta_dal_balcone}
      death: true              # facoltativo, default false
      text: …
```

- Modelli: `GameInfo.acts: tuple[Act, ...] = ()`, con `Act(name: Text, when: Condition)`;
  `Ending.death: bool = False`.
- `GameState` ha tre campi nuovi, con valori predefiniti, così i salvataggi di oggi restano validi:
  - `act: int = 0` — quanti atti sono cominciati;
  - `checkpoint: dict | None = None` — lo stato all'inizio dell'ultimo atto cominciato, in JSON;
  - `lost: bool = False` — la partita è finita con una morte.
- `Engine.execute`, dopo l'azione e il conteggio del turno e prima dei finali: se la condizione
  dell'atto successivo (`acts[state.act]`) vale, `state.act += 1` e `state.checkpoint` diventa la
  copia dello stato (senza il suo `checkpoint`). Poi i finali: un finale con `death` imposta anche
  `lost`.
- `Engine.resume(state) -> (GameState, Outcome)`: se la partita è persa e c'è un checkpoint, lo
  stato ripreso è quella copia (che conserva lo stesso checkpoint, così si può morire e riprendere
  ancora); l'esito ha il testo «Riprendi dall'inizio del secondo atto.» e la stanza. Altrimenti
  errore.
- `Engine.restore` controlla anche lo stato dentro `checkpoint`.
- `Game.turn("riprendi")` su una partita persa con checkpoint la riprende; su una partita finita,
  qualunque altra riga risponde «La partita è finita.» senza passare dall'LLM. L'invito a
  riprendere lo scrivono i front end: la pagina, con `resumable` (il nome dell'atto), «[Scrivi
  «riprendi» per ricominciare dall'inizio del secondo atto, oppure scegli «Nuova partita».]»; il
  terminale con la sua domanda.
- **Web**: la risposta di `/api/turn` ha un campo nuovo, `resumable`: il nome dell'atto da cui si
  può riprendere, oppure niente. La pagina lascia l'input attivo in quel caso, con il suggerimento
  «riprendi»; «Nuova partita» resta nella riga di stato.
- **Terminale**: dopo una morte con checkpoint, «Vuoi riprendere dall'inizio del secondo atto?
  (s/n)»; con un no, la domanda di oggi, «Vuoi giocare ancora?».
- **La Rocca**: il finale del pozzo prende `death: true`; senza atti non c'è checkpoint, quindi si
  ricomincia da capo come oggi.

### 5.3 Varianti di `otherwise` nelle regole

`Rule.otherwise_variants: tuple[TextVariant, ...] = ()`, come per le uscite: quando `when` è falso,
la prima variante valida sostituisce `otherwise`. Serve a quasi tutti i meccanismi della pista
(«non gira: c'è la ruggine» / «lo scomparto è vuoto»).

### Documentazione e test

- `docs/formato-mondo.md`: `moves`, `acts`, `death`, `otherwise_variants` delle regole, e i
  pericoli («morire entrando in una stanza» con `player_in`).
- Test del motore sul mondo di prova per ognuna delle tre aggiunte; test di `Game` per «riprendi»;
  test web per `resumable`; test del terminale per la domanda dopo la morte; `Engine.restore` con
  checkpoint; la Rocca: il pozzo è una morte, ma senza ripresa.

---

## 6. Costruzione e prove

- **Dati**: `data/worlds/valdimora/`, con `gioco.yaml`, `personaggi.yaml` e un file per piano
  (`pianterreno.yaml`, `piano-nobile.yaml`, `soffitta.yaml`, `cantina.yaml`) con stanze, oggetti e
  regole di quel piano. `avventure.yaml` elenca `valdimora` dal primo atto, con un finale
  provvisorio a ogni atto.
- **Testi**: li scrive Claude, l'utente li rilegge nella PR. La protagonista al femminile; i
  domestici danno del voi («signorina»); registro del 1927, senza anacronismi; le descrizioni
  nominano le stanze vicine; un indizio che manda a fare qualcosa ha una variante per quando è
  fatto (regola di CLAUDE.md).
- **Nomi degli oggetti distinti**, perché il parser non chieda sempre «Quale intendi»: le lettere
  sono quattro — la lettera della contessa (quella di Irene), le lettere per Clara (il pacco nel
  baule), la lettera di giugno (intercettata) e la lettera del notaio — e anche chiavi e biglietti
  hanno ciascuno un nome proprio (chiave dello scalone, chiave della credenza, chiavetta di
  carica…).
- **Test** in `tests/test_valdimora.py`, a ogni atto:
  - la soluzione dell'atto giocata con comandi semplici attraverso `Game`, controllando i testi
    chiave; nell'atto 4 la partita intera per ognuno dei tre finali;
  - ogni filo facoltativo e ogni pericolo: la morte avviene, e «riprendi» riporta all'inizio
    dell'atto;
  - invarianti, come in `tests/test_castello.py`: la chiave di ogni piano solo dalla sua regola;
    il medaglione non si lascia né si perde; nessun oggetto che serve in cantina sta di sopra;
    nessun argomento dei personaggi con effetti che accorcino la pista (tranne quelli previsti).
- **Il modello vero**: ogni atto si gioca con frasi libere; le frasi sbagliate in
  `logs/comandi.jsonl` diventano casi di `tests/test_ollama.py`, col test sul client finto
  accanto. Esempi nel prompt solo in `game.examples` di Valdimora e solo se servono, verificati su
  tutto `tests/test_ollama.py`.

## Fuori ambito

- Verbi nuovi (accendi, suona, mostra, accusa…): le azioni passano per `usa`, `dai`, `chiedi`.
- Personaggi che si muovono da soli col passare del tempo: si spostano solo con i flag.
- Il tempo che passa, il buio calcolato stanza per stanza (la lanterna serve solo a scendere).
- Un quarto finale segreto (i segreti di tutti): si potrà aggiungere dopo.
- «salva»/«carica» a comando: c'è solo il salvataggio automatico degli atti.

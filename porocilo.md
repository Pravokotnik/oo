# Poročilo o prvi projektni nalogi

### Uvod 

Naša skupina si je izbrala temo "Ogled velike zbirke slikarskih del". Oblikovali bomo spletno aplikacijo, ki bo delovala kot vmesnik za prikaz velike zbirke slikarskih del. Vmesnik je zasnovan kot virtualen učni pripomoček, namenjen uporabnikom, ki jih zanimajo osnove umetne zaznave (computer vision) in analiza vizualnih značilnosti.

Cilj projekta je uporabniku na konkretnem primeru prikazati, kako računalnik vidi in interpretira sliko, ter ga ob tem seznaniti z umetniškimi deli. Računalniški vid želimo prikazati na razumljiv in zabaven način, hkrati pa nameniti pozornost tudi umetnikom, katerih ustvarjalnost v času razmaha umetne inteligence pogosto izgublja zasluženo prepoznavnost.

### Rešitev

Naša rešitev bo implementirana kot spletna aplikacija, kjer bo uporabnik lahko:
+ brskal po zbirki umetniških del
+ filtriral slike po različnih vizualnih lastnostih (barva - odtenek in nasičenost, poze ljudi, emocije obrazov, robovi, objekti)
+ izbral želeno telesno pozo, na podlagi katere bo sistem prikazal slike z osebami v podobni drži
+ spremljal korake umetne zaznave (faze Hough transformacije za zaznavo robov in rezultati Houghove transformacije)

Aplikacija bo imela tudi učni značaj, saj bo poleg rezultatov ponujala tudi vizualno razlago vsakega postopka obdelave slike.

### Načrt

Projekt bomo razdelili na več funkcionalnih sklopov:
+ zbirka slik – uvoz in organizacija umetniških del
+ obdelava slik - barvna analiza, Canny, Hough, detekcija oseb, detekcija poz, detekcija objektov
+ uporabniški vmesnik – frontend z možnostjo izbire slike in prikaza postopkov
+ navigacija in filtriranje – možnost iskanja po slikah glede na določene kriterije
+ vizualizacija postopkov – prikaz posameznih korakov zaznave (npr. izhod vsake faze pri Hough transformaciji)

### Podobni projekti

Na spletu smo našli nekaj podobnih projektov:
+ Teachable machine: https://teachablemachine.withgoogle.com/
+ ARTETIK: From the Art: https://artsandculture.google.com/color?project=guggenheim-bilbao&col=RGB_3F9CEF

Četudi se te nanašajo na podobne koncepte, menimo da niso dosegli nivo interaktivnosti, preprostosti in poučnosti, ki jo želimo doseči s svojim projektom.

### Scenarij

1. Uporabnik odpre spletno stran, kjer ga pričaka vstopni zaslon z dobrodšlico
2. Ob pomiku navzdol se uporabniku prikaže umetnik s platnom
3. Ob kliku na XRAY očala se stilno spremeni scena, kar ponudi možnosti za nadaljno analizo umetniških del:
    + Obraz
    + Poza
    + Barvna kompozicija
    + Zaznane ravne črte in krogi
    + Zaznani objekti in njihova velikost
4. Uporabnik izbere eno izmed ponujenih možnosti, kar sproži prilagojen prikaz
5. Prilagojeni prikaz in analiza:
    + Mrežni prikaz:
        + Prikaz podobnih del
        + Po kliku na sliko se uporabniku odpre poseben prikaz slike
    + Prikaz slike:
        + Ob sliki je zapisana razlaga, zakaj je bila ta slika izbrana
        + Barve:
            + Prikaz histograma barvne razporeditve
            + Uporabnik lahko prilagaja histogram, glede na prilagojenega se prikaže novo delo, katerega histogram je najbolj podoben temu
        + Poza:
            + Prikaz lutke v zaznani pozi
            + Ko uporabnik spremeni pozo lutke, se prikaže animacija slik iz prejšnje poze v spremenjeno
        + Obraz:
            + Prikaz skale sreče
        + Hough:
            + Ob premiku drsnika se prikažejo vmesni koraki Hough transformacije
            + Igrifikacija: 
                + Kateri sliki pripadajo krogi in črte
                + Uporabnik nariše kroge in črte, sistem prikaže slike s podobnimi elementi
                + Uporabnik lahko pobarva svoj Hough prostor, sistem prikaže slike s podobnimi elementi
        + Zaznava objektov:
            + Prikaz zaznih objektov na sliki
            + S pomikanjem koleščka na miški se simulira občutek povečanja ali manjšanja izbranega objekta z menjavo umetniškega dela na takšnega, kjer je izbrani objekt malo manjši ali večji

### Vmesnik

Uporabniški vmesnik spletne aplikacije bo zasnovan na interaktiven in vizualno privlačen način, z namenom, da uporabnika intuitivno vodi skozi izkušnjo učenja in raziskovanja umetnosti skozi računalniški vid.

Glavne komponente vmesnika:
+ **Začetni zaslon:**
    Prvi prikaz uporabniku vključuje pozdravno sporočilo.
+ **Slikar in platno:**
Ob pomiku po strani navzdol se prikaže umetnik s platnom. Ta element uvaja glavni interaktivni del aplikacije.
+ **XRAY očala – nadzorni meni**
   Ob kliku na XRAY očala se scena pretvori v "XRAY" pogled, kjer ima uporabnik označene objekte, na katere lahko klikne. Vsak objekt odpre svoj način urejanja slik:
    + Obraz - sortiranje slik glede na emocije zaznanih obrazov, prikaz obrazov izrezanih iz slik glede na trenutno vreme, kjer je sončno veselo, deževno pa žalostno, uporabnik lahko premika sonce
    + Poza - gručenje slik po zaznani pozi osebe
    + Barvna kompozicija - prikaz slik po podobnosti barve v mrežni kompoziciji v stilu HSV izbornika barve
    + Hough - prikaz gručenih slik po podobnosti zaznanih črt in krogov, gumb za igrifikacijo
    + Objekt - prikaz nakljčne slike z označenimi zaznanimi objekti
    
    Na vsakem od prikazov lahko uporabnik izbere poljubno sliko. Ob kliku nanjo se odpre podrobnejša analiza rezultata in opis postopka pridobitve le-tega.
+ **Prikaz slike in analiza rezultata:**
    + Obraz: 
        + Brez posebnosti.
    + Poza:
        + Uporabnik ima na desni strani zaslona lutko, katero lahko premika v želeno pozo z drag-and-drop interakcijo, na levi strani pa se slika spreminja glede na pozo.
        + Ob kliku na "play" gumb se prične animacija, kjer se zaporedoma prikazujejo slike s podobnimi, vendar malo drugačnimi pozami.
    + Barvna kompozicija:
        + Na desni strani zaslona ima uporabnik dostop do histograma barvne analize izbrane slike. Uporabnik lahko histogram poljubno spreminja. Ob spremembi se slika na levi strani zaslona spremeni v tisto, z najbolj podobnim histogramom narisanemu.
    + Hough:
        + Na levi strani zaslona ima uporabnik dostop do drsnika, s katerim lahko izbere korak v postopku zaznave črt in krogov s Hough transformacijo.
        + Na desni strani ima uporabnik prikazan Hough prostor trenutne slike. Ko je uporabnik na prikazu zaznave robov (eden izmed korakov drsnika), lahko spreminja Hough prostor ali prikaz robov tako da obarva nove piksle. Ob spremembi ene izmed teh dveh, se skladno spremeni tudi druga.
        + Ko je uporabnik na prikazu slike lahko uporabi orodje za risanje črt in krogov. V tem primeru se bo slika zamenjala s tisto, ki ima like na najbolj podobnih pozicijah.
    + Objekt:
        + Ko uporabnik klikne na objekt se ta centrira na zaslon. Premik koleščka na miški nato najde sliko, kjer je enak objekt prikazan večji ali manjši, odvisno od premika. 

    Vedno bo pod prikazom slike naveden opis uporabljenega postopka za pridobitev trenutnega rezultata. 
+ **Igrifikacija:**
    Igrifikacijo bomo vključili pri Hough transformaciji. Ko uporabnik klikne na gumb za igrifikacijo, se odpre nov zaslon, kjer sistem izbere 3 naključne slike ter za eno izmed njih prikaže njene zaznane črte in kroge. Uporabnik mora nato izbrati tisto sliko, ki se ujema z liki. Cilj je zadeti čim več pravilnih zaporednih poskusov.

### Gradivo

1. Zbirka umetniških del:
    Celoten zip baze bomo pridobili na eni izmed spodnjih povezav:
    + https://forums.fast.ai/t/the-wikiart-dataset/27831
    + https://github.com/cs-chan/ArtGAN/blob/master/WikiArt%20Dataset/README.md

2. Vizualna analiza in umetna zaznava:
    + OpenCV

3. Strojno učenje in umetna inteligenca:
    + Gručenje, post-procesiranje in redukcija dimenzij s scikit-learn
    + Uporaba pre-trained modelov s TensorFlow
    + Zaznava obrazov in objektov z YOLO

4. Uporabniški vmesnik in oblikovanje:
    + HTML, CSS, TypeScript za spletno stran
    + Modele bomo naredili sami (slikar, paleta, očala...)

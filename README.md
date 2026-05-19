# Subiekt GT -> KSeF XML Generator (FA(3))

Prosty skrypt do wyciągania danych z bazy Subiekta GT (MSSQL) i generowania plików XML zgodnych ze strukturą **FA(3)** dla KSeF.

## Jak to ugryźć?

1. **Wymagania**: Musisz mieć zainstalowane `pyodbc` (do bazy) i `python-dotenv` (do konfiguracji). Wszystko jest w `requirements.txt`.
2. **Konfiguracja**:
   - Skopiuj plik `.env.example` i zmień mu nazwę na `.env`.
   - Wpisz tam dane do swojej bazy (IP serwera, nazwa bazy, użytkownik SQL).
3. **Uruchomienie**:
   - Żeby zobaczyć ostatnie 10 faktur i sprawdzić czy połączenie działa, odpal: `python list_invoices.py`.
   - Żeby wygenerować XML dla najnowszej faktury, odpal: `python main.py`.

## Logika generowania XML FA(3) (Stan na 2026-05-19)

Generator został dostosowany do oficjalnych przykładów MF dla struktury logicznej FA(3).

### 1. Mapowanie Rodzajów Transakcji (Stawka 0%)
Dla pozycji ze stawką 0% system stosuje inteligentne rozróżnienie na podstawie kraju kontrahenta i rodzaju kartoteki (`tw_Rodzaj`):

- **WDT (Wewnątrzwspólnotowa Dostawa Towarów)**:
  - Warunek: Towar (Rodzaj 1) + Kraj UE (poza PL) + Stawka 0%.
  - KSeF: Pole `<P_13_6_2>`, Wiersz `<P_12>0 WDT</P_12>`, Adnotacja `P_18=2`.
- **Eksport Towarów**:
  - Warunek: Towar (Rodzaj 1) + Kraj poza UE + Stawka 0%.
  - KSeF: Pole `<P_13_6_3>`, Wiersz `<P_12>0 EX</P_12>`, Adnotacja `P_18=2`.
- **Odwrotne Obciążenie (OO / Eksport Usług)**:
  - Warunek: Usługa (Rodzaj 2) + dowolny kraj + Stawka 0% LUB dowolny rodzaj + Kraj PL + Stawka 0% LUB brak stawki (null).
  - KSeF: Pole `<P_13_7>`, Wiersz `<P_12>oo</P_12>`, Adnotacja **`P_18=1`**.

### 2. Transakcje Krajowe (Standard)
- Stawki 23%, 8%, 5% są mapowane odpowiednio do `P_13_1/P_14_1`, `P_13_2/P_14_2`, `P_13_3/P_14_3`.
- `P_12` w wierszu zawiera wartość liczbową (np. "23").

### 3. Wymogi Techniczne i Strukturalne
- **Kolejność elementów**: W sekcji `DaneIdentyfikacyjne` identyfikatory (NIP/KodUE/NrID) są zawsze przed nazwą podmiotu (wymóg XSD).
- **UU_ID**: Każdy wiersz faktury posiada unikalny 16-znakowy identyfikator.
- **Data (P_1)**: Używana jest data wystawienia z dokumentu źródłowego.
- **Adnotacje**: Pola P_19, P_22, P_PMarzy są elementami strukturalnymi (np. `<Zwolnienie><P_19N>1</P_19N></Zwolnienie>`).
- **Waluty**: Przy walutach obcych generator pobiera kurs NBP z dnia roboczego poprzedzającego zdarzenie i dodaje tag `KursWaluty` w wierszach.

Pliki XML lądują w głównym folderze z nazwą typu `KSeF_FS_123_2026.xml`.

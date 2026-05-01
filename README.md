# Subiekt GT -> KSeF XML Generator

Prosty skrypt do wyciągania danych z bazy Subiekta GT (MSSQL) i generowania plików XML zgodnych ze strukturą FA(3) dla KSeF.

## Jak to ugryźć?

1. **Wymagania**: Musisz mieć zainstalowane `pyodbc` (do bazy) i `python-dotenv` (do konfiguracji). Wszystko jest w `requirements.txt`.
2. **Konfiguracja**:
   - Skopiuj plik `.env.example` i zmień mu nazwę na `.env`.
   - Wpisz tam dane do swojej bazy (IP serwera, nazwa bazy, użytkownik SQL).
3. **Uruchomienie**:
   - Żeby zobaczyć ostatnie 10 faktur i sprawdzić czy połączenie działa, odpal: `python list_invoices.py`.
   - Żeby wygenerować XML dla najnowszej faktury, odpal: `python main.py`.

## Co to robi?
- Obsługuje faktury krajowe, WDT (UE) i Eksport.
- Automatycznie wykrywa walutę (PLN/EUR).
- Mapuje stawki 0% na odpowiednie kody (0 WDT, 0 EX, 0 KR).
- Obsługuje Odwrotne Obciążenie (oo).
- Przelicza ceny jednostkowe tak, żeby walidator KSeF nie wywalał błędów o zaokrąglenia.

Pliki XML lądują w głównym folderze z nazwą typu `KSeF_FS_123_2024.xml`.

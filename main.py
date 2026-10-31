import sqlite3
import asyncio
import aiohttp
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from aiohttp import web

# ==========================================
# 1. CONFIGURAZIONE DATABASE E AMBIENTE
# ==========================================
load_dotenv()
mio_id_telegram = int(os.getenv("MIO_ID"))
BOT_TOKEN = os.getenv("BOT_TOKEN")

STAZIONE_1 = os.getenv("STAZIONE_1", "STAZIONE1")
STAZIONE_2 = os.getenv("STAZIONE_2", "STAZIONE2")
TRENO_1 = os.getenv("TRENO_1", "00000")
TRENO_2 = os.getenv("TRENO_2", "00001")
conn = sqlite3.connect('treni.db')
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS preferenze_treni (
    telegram_id INTEGER,
    orario TEXT,
    numero_treno TEXT
)
''')

# Resetta i vecchi dati per evitare duplicati
cursor.execute("DELETE FROM preferenze_treni WHERE telegram_id = ?", (mio_id_telegram,))

# Inserisci i tuoi orari
cursor.execute("INSERT INTO preferenze_treni (telegram_id, orario, numero_treno) VALUES (?, ?, ?)", 
               (mio_id_telegram, "06:56", TRENO_1))
cursor.execute("INSERT INTO preferenze_treni (telegram_id, orario, numero_treno) VALUES (?, ?, ?)", 
               (mio_id_telegram, "08:56", TRENO_2))

conn.commit()
conn.close()

# ==========================================
# 2. MOTORE DI RICERCA TRENI (API)
# ==========================================
async def ottieni_stato_treno(numero_treno):
    url_ricerca = f"http://www.viaggiatreno.it/infomobilita/resteasy/viaggiatreno/cercaNumeroTrenoTrenoAutocomplete/{numero_treno}"
    headers_browser = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    async with aiohttp.ClientSession(headers=headers_browser) as session:
        async with session.get(url_ricerca) as response:
            testo_risposta = await response.text()
            
        if not testo_risposta.strip():
            return f"Treno {numero_treno} non trovato o non circolante oggi."
            
        prima_riga = testo_risposta.strip().split('\n')[0]
        if '|' not in prima_riga:
            return f"Errore: Formato imprevisto. Risposta: {prima_riga}"
            
        try:
            frammenti = prima_riga.split('|')[1].split('-')
            codice_stazione = frammenti[1]
            timestamp = frammenti[2]
        except IndexError:
            return f"Errore nel parsing dei dati stazione per il treno {numero_treno}."
        
        url_stato = f"http://www.viaggiatreno.it/infomobilita/resteasy/viaggiatreno/andamentoTreno/{codice_stazione}/{numero_treno}/{timestamp}"
        
        async with session.get(url_stato) as response:
            if response.status != 200:
                return f"Errore {response.status}: Impossibile scaricare i dati."
            dati_treno = await response.json()
            
        origine = dati_treno.get('origine', 'Sconosciuta')
        destinazione = dati_treno.get('destinazione', 'Sconosciuta')
        ritardo = dati_treno.get('ritardo', 0)
        provvedimento = dati_treno.get('tipoProvedimento', 0)
        
        if provvedimento == 1:
            stato = "SOPPRESSO"
        elif provvedimento == 2:
            stato = "LIMITATO"
        elif dati_treno.get('nonPartito'):
            stato = "Non ancora partito"
        else:
            ultimo_rilevamento = dati_treno.get('stazioneUltimoRilevamento', 'In viaggio')
            stato = f"In viaggio (Ultimo rilevamento: {ultimo_rilevamento})"
            
        messaggio = (
            f"Treno {numero_treno}: ({origine} -> {destinazione})\n"
            f"Stato: {stato}\n"
            f"Ritardo attuale: {ritardo} minuti"
        )
        return messaggio

# ==========================================
# 3. INTERFACCIA BOT TELEGRAM
# ==========================================
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("stop"))
async def ferma_bot(message: types.Message):
    if message.from_user.id == mio_id_telegram:
        await message.answer("Spegnimento del bot in corso...")
        await dp.stop_polling()
    else:
        await message.answer("Accesso negato.")

@dp.message()
async def rispondi_con_stato_treno(message: types.Message):
    orario_richiesto = message.text.strip()
    id_utente = message.from_user.id
    
    conn = sqlite3.connect('treni.db')
    cursor = conn.cursor()
    cursor.execute("SELECT numero_treno FROM preferenze_treni WHERE telegram_id = ? AND orario = ?", (id_utente, orario_richiesto))
    risultato = cursor.fetchone()
    conn.close()
    
    if risultato:
        numero_treno = risultato[0]
        messaggio_attesa = await message.answer(f" Controllo il treno {numero_treno}...")
        stato_finale = await ottieni_stato_treno(numero_treno)
        await messaggio_attesa.edit_text(stato_finale)
    else:
        await message.answer(f"Nessun treno salvato per le ore '{orario_richiesto}'.")

# ==========================================
# 4. LOGICA NOTIFICHE MATTUTINE (AIRUNO/OLGIATE)
# ==========================================
async def controllo_automatico_mattina(numero_treno):
    await bot.send_message(chat_id=mio_id_telegram, text=f"Buongiorno! Inizio il monitoraggio del treno {numero_treno}. ")
    stato_finale = await ottieni_stato_treno(numero_treno)
    
    tentativi = 0
    while "STAZIONE_1" not in stato_finale.upper() and "STAZIONE_2" not in stato_finale.upper() and tentativi < 30:
        await asyncio.sleep(120) 
        stato_finale = await ottieni_stato_treno(numero_treno)
        
        # 1° Check: Controllo soppressione o limitazione
        if "SOPPRESSO" in stato_finale:
            await bot.send_message(chat_id=mio_id_telegram, text=f"ATTENZIONE: Il treno è stato soppresso\n\n{stato_finale}")
            return 

        if "LIMITATO" in stato_finale:
            await bot.send_message(chat_id=mio_id_telegram, text=f"ATTENZIONE: Il treno è stato limitato\n\n{stato_finale}")
            return
            
        tentativi += 1

    if "STAZIONE_1" in stato_finale.upper() or "STAZIONE_2" in stato_finale.upper():
        await bot.send_message(
            chat_id=mio_id_telegram, 
            text=f"Il treno ha superato Airuno ed è in arrivo!\n\n{stato_finale}"
        )

# ==========================================
# 5. FINTO SERVER WEB PER RENDER.COM
# ==========================================
async def web_server_handler(request):
    return web.Response(text="Il bot di monitoraggio treni è attivo e funzionante!")

async def avvia_server_fittizio():
    app = web.Application()
    app.router.add_get('/', web_server_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

# ==========================================
# 6. SCHEDULER E AVVIO BOT
# ==========================================
async def avvia_bot():
    scheduler = AsyncIOScheduler()
    
    scheduler.add_job(
        controllo_automatico_mattina, 
        'cron', 
        day_of_week='mon', 
        hour=6, 
        minute=38, 
        args=["TRENO_1"]
    )
    
    scheduler.add_job(
        controllo_automatico_mattina, 
        'cron', 
        day_of_week='tue-fri', 
        hour=8, 
        minute=38, 
        args=["TRENO_2"]
    )
    
    scheduler.start()
    
    # Avviamo il finto sito web in background
    await avvia_server_fittizio()
    
    print("Bot avviato! Scheduler e finto web server attivi. In attesa di messaggi...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(avvia_bot())

import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  ArrowLeft, ArrowRight, BadgeCheck, BookOpen, CarFront, Check, CheckCheck,
  CheckCircle2, ChevronRight, CircleHelp, ClipboardCheck, GraduationCap,
  ListChecks, MapPin, PartyPopper, RotateCcw, Send, Sparkles, Trophy,
  UserRound, X
} from 'lucide-react';
import './training.css';

const STEPS = [
  ['MENU', 'Inicie a conversa'],
  ['Escolher Tour', 'Selecione seu Tour'],
  ['Solicitar', 'Peça o carrinho'],
  ['Casa', 'Solicite a próxima etapa'],
  ['Galeria', 'Escolha o destino'],
  ['Destino', 'Peça o carrinho final'],
  ['Finalizar', 'Conclua o fluxo']
];

const MODES = {
  GUIDED: { label: 'Treino guiado', detail: 'com dicas', icon: BookOpen },
  NORMAL: { label: 'Treino normal', detail: 'sem dicas', icon: GraduationCap },
  TEST: { label: 'Teste final', detail: 'avaliação', icon: ClipboardCheck }
};

const TOURS = [
  { id: 'tour-3', label: 'Tour 3', wave: '1ª Ola', state: 'disponível' },
  { id: 'tour-4', label: 'Tour 4', wave: '1ª Ola', state: 'disponível' },
  { id: 'tour-5', label: 'Tour 5', wave: '2ª Ola', state: 'disponível' }
];

const DESTINATIONS = [
  { id: 'lobby-selection', name: 'Lobby Selection', type: 'Lobby' },
  { id: 'lobby-waves', name: 'Lobby Waves', type: 'Lobby' },
  { id: 'prestige-selection', name: 'Prestige Selection', type: 'Prestige' },
  { id: 'prestige-waves', name: 'Prestige Waves', type: 'Prestige' }
];

function hintFor(step, tour, destination) {
  const hints = [
    'No WhatsApp real, envie MENU para receber os Tours disponíveis.',
    'Toque em “Ver opções” e escolha apenas o Tour da sua Ola.',
    'Depois de selecionar o Tour, confirme em “Solicitar carrinho”.',
    'A mensagem do sistema confirma o pedido e mostra os motoristas disponíveis.',
    'Na Galeria, abra “Escolher destino” para registrar a saída do grupo.',
    'No WhatsApp, tocar no destino já envia o pedido do último carrinho.',
    `Fluxo concluído: ${tour?.label || 'Tour'} → Casa → Galeria → ${destination?.name || 'destino'}.`
  ];
  return hints[step] || hints[0];
}

function Progress({ step }) {
  return <ol className="training-progress" aria-label="Etapas do treinamento">{STEPS.map(([label], index) => <li key={label} className={index <= step ? 'done' : ''}><span>{index < step ? <Check size={12} /> : index + 1}</span><small>{label}</small></li>)}</ol>;
}

function Bubble({ children, mine = false, business = false, time = 'agora' }) {
  return <article className={`chat-message ${mine ? 'mine' : ''}`}>
    {!mine && business && <p className="business-name">The Club · Carrinhos</p>}
    <div className="chat-bubble">{children}<span className="chat-time">{time}{mine && <CheckCheck size={13} />}</span></div>
  </article>;
}

function WhatsAppAction({ children, onClick, list = false, secondary = false }) {
  return <button type="button" className={`whatsapp-action ${secondary ? 'secondary' : ''}`} onClick={onClick}>{list ? <ListChecks size={18} /> : <ArrowRight size={18} />}{children}</button>;
}

function Availability() {
  return <p className="availability"><strong>Disponibilidade dos motoristas agora:</strong><br />Lucas: ✅ Disponível<br />Marcos: 🚘 Em tour com Carolina<br />Rafael: ❌ Folga - Férias</p>;
}

function GuidedHint({ step, tour, destination }) {
  return <aside className="training-hint"><Sparkles size={21} /><div><strong>Passo {Math.min(step + 1, STEPS.length)} de {STEPS.length}</strong><p>{hintFor(step, tour, destination)}</p></div></aside>;
}

function App() {
  const [name, setName] = useState('');
  const [mode, setMode] = useState('GUIDED');
  const [started, setStarted] = useState(false);
  const [step, setStep] = useState(0);
  const [tour, setTour] = useState(null);
  const [destination, setDestination] = useState(null);
  const [showTourPicker, setShowTourPicker] = useState(false);
  const [showDestinationPicker, setShowDestinationPicker] = useState(false);

  const firstName = name.trim().split(/\s+/)[0] || 'consultor';
  const guided = mode === 'GUIDED';
  const finished = step === STEPS.length - 1;

  useEffect(() => {
    if (step !== 5 || !destination) return undefined;
    const completionTimer = window.setTimeout(() => setStep(6), 650);
    return () => window.clearTimeout(completionTimer);
  }, [destination, step]);

  function startTraining() {
    setStarted(true);
    setStep(0);
    setTour(null);
    setDestination(null);
  }

  function reset() {
    setStarted(false);
    setStep(0);
    setTour(null);
    setDestination(null);
    setShowTourPicker(false);
    setShowDestinationPicker(false);
  }

  function beginConversation() { setStep(1); }

  function chooseTour(item) {
    setTour(item);
    setShowTourPicker(false);
    setStep(2);
  }

  function requestFirstCart() { setStep(3); }

  function requestFromCasa() { setStep(4); }

  function chooseDestination(item) {
    setDestination(item);
    setShowDestinationPicker(false);
    setStep(5);
  }

  if (!started) {
    return <main className="training-welcome">
      <section className="welcome-card">
        <div className="welcome-lock"><BadgeCheck size={18} /> Link privado de treinamento</div>
        <div className="welcome-icon"><CarFront size={42} /></div>
        <p className="eyebrow">THE CLUB · CARRINHOS</p>
        <h1>Simulador de treinamento</h1>
        <p className="welcome-copy">Treine exatamente o fluxo do WhatsApp: MENU, escolha do Tour, solicitação, Casa, Galeria e destino final.</p>
        <label className="name-field"><UserRound size={18} /><input value={name} onChange={(event) => setName(event.target.value)} placeholder="Seu nome" autoComplete="name" /></label>
        <fieldset className="mode-fieldset"><legend>Selecione o modo de treino</legend>{Object.entries(MODES).map(([key, item]) => { const Icon = item.icon; return <button type="button" onClick={() => setMode(key)} className={`mode-option ${mode === key ? 'selected' : ''}`} key={key}><Icon size={21} /><span><strong>{item.label}</strong><small>{item.detail}</small></span>{mode === key && <CheckCircle2 size={20} />}</button>; })}</fieldset>
        <button className="start-button" type="button" onClick={startTraining}>Iniciar treinamento <ArrowRight size={19} /></button>
        <p className="private-note"><CircleHelp size={15} /> Este ambiente não cria solicitações reais.</p>
      </section>
    </main>;
  }

  return <main className="training-app">
    <header className="training-header">
      <button type="button" className="icon-button" onClick={reset} aria-label="Voltar ao início"><ArrowLeft size={21} /></button>
      <span className="brand-mark"><CarFront size={20} /></span>
      <div><strong>The Club · Carrinhos</strong><small>Simulador de Treinamento</small></div>
      <span className="mode-badge">{MODES[mode].label}</span>
    </header>
    <Progress step={step} />
    <section className="training-stage">
      <div className="chat-shell">
        <div className="chat-background" />
        <div className="chat-content">
          {step >= 1 && <Bubble mine time="19:27">MENU</Bubble>}
          {step >= 1 && <Bubble business time="19:27"><p>Olá, {firstName}. Há 3 Tour(es) disponível(is). Escolha o seu Tour para solicitar o carrinho no Prestige.</p><WhatsAppAction list onClick={() => setShowTourPicker(true)}>Ver opções</WhatsAppAction></Bubble>}
          {tour && <Bubble mine time="19:28">{tour.label}<small>{tour.wave} · disponível</small></Bubble>}
          {step >= 2 && tour && <Bubble business time="19:28"><p>{tour.label} selecionado. Confirme para solicitar o carrinho no Prestige.</p><WhatsAppAction onClick={requestFirstCart}>Solicitar carrinho</WhatsAppAction><WhatsAppAction secondary onClick={() => { setTour(null); setStep(1); }}>Voltar</WhatsAppAction></Bubble>}
          {step >= 3 && tour && <Bubble mine time="19:28">Solicitar carrinho</Bubble>}
          {step >= 3 && tour && <Bubble business time="19:28"><p>Solicitação enviada: {tour.label} em Prestige Selection. Aguarde um motorista assumir.</p><Availability /></Bubble>}
          {step >= 3 && tour && <Bubble business time="19:29"><p>Lucas assumiu {tour.label}. O atendimento está em andamento.</p></Bubble>}
          {step >= 3 && tour && <Bubble business time="19:29"><p>{tour.label}: o motorista foi liberado e você está aguardando na Casa. Quando precisar, solicite outro carrinho.</p><WhatsAppAction onClick={requestFromCasa}>Solicitar na Casa</WhatsAppAction></Bubble>}
          {step >= 4 && tour && <Bubble mine time="19:30">Solicitar na Casa</Bubble>}
          {step >= 4 && tour && <Bubble business time="19:30"><p>Solicitação enviada: {tour.label} em Casa. Aguarde um motorista assumir.</p><Availability /></Bubble>}
          {step >= 4 && tour && <Bubble business time="19:30"><p>Lucas assumiu {tour.label}. O atendimento está em andamento.</p></Bubble>}
          {step >= 4 && tour && <Bubble business time="19:31"><p>{tour.label} chegou à Galeria. Escolha o destino para solicitar um carrinho.</p><WhatsAppAction list onClick={() => setShowDestinationPicker(true)}>Escolher destino</WhatsAppAction></Bubble>}
          {destination && <Bubble mine time="19:31">{destination.name}<small>Solicitar carrinho</small></Bubble>}
          {step >= 5 && destination && <Bubble business time="19:32"><p>Solicitação enviada: {tour.label} da Galeria para {destination.name}. Aguarde um motorista assumir.</p><Availability /></Bubble>}
          {finished && destination && <Bubble business time="19:33"><p>Lucas assumiu {tour.label}. O atendimento está em andamento.</p></Bubble>}
          {finished && destination && <Bubble business time="19:34"><p>{tour.label} foi finalizado. Obrigado. Envie MENU quando precisar iniciar outro Tour.</p></Bubble>}
          {guided && !finished && <GuidedHint step={step} tour={tour} destination={destination} />}
          {finished && <aside className="training-complete"><PartyPopper size={30} /><div><strong>Treinamento concluído!</strong><p>Você completou o Tour simulado com sucesso.</p></div></aside>}
        </div>
        <div className="whatsapp-composer">
          <span>{step === 0 ? 'Digite MENU para iniciar' : 'Digite uma mensagem'}</span>
          {step === 0 ? <button type="button" onClick={beginConversation} aria-label="Enviar MENU"><Send size={19} /></button> : <button type="button" onClick={reset} aria-label="Refazer treinamento"><RotateCcw size={19} /></button>}
        </div>
      </div>
    </section>
    <footer className="training-footer"><span><Trophy size={17} /> Progresso: {Math.min(100, Math.round((step / (STEPS.length - 1)) * 100))}%</span><span>{tour?.label || 'Tour pendente'} {destination ? `· ${destination.name}` : ''}</span></footer>

    {showTourPicker && <div className="training-modal-backdrop" role="presentation"><section className="training-modal" role="dialog" aria-modal="true" aria-label="Escolher Tour"><button className="modal-close" type="button" onClick={() => setShowTourPicker(false)} aria-label="Fechar"><X size={21} /></button><span className="modal-handle" /><h2>Escolher Tour</h2><p>Opções recebidas no WhatsApp.</p><div className="choice-list">{TOURS.map((item) => <button key={item.id} type="button" onClick={() => chooseTour(item)}><span className="choice-icon"><UserRound size={18} /></span><span><strong>{item.label}</strong><small>{item.wave} · {item.state}</small></span><ChevronRight size={18} /></button>)}</div></section></div>}
    {showDestinationPicker && <div className="training-modal-backdrop" role="presentation"><section className="training-modal" role="dialog" aria-modal="true" aria-label="Escolher destino"><button className="modal-close" type="button" onClick={() => setShowDestinationPicker(false)} aria-label="Fechar"><X size={21} /></button><span className="modal-handle" /><h2>Escolher destino</h2><p>Opções recebidas no WhatsApp.</p><div className="choice-list">{DESTINATIONS.map((item) => <button key={item.id} type="button" onClick={() => chooseDestination(item)}><span className="choice-icon destination"><MapPin size={18} /></span><span><strong>{item.name}</strong><small>Solicitar carrinho</small></span><ChevronRight size={18} /></button>)}</div></section></div>}
  </main>;
}

createRoot(document.getElementById('root')).render(<App />);

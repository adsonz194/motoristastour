import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  ArrowLeft, ArrowRight, BadgeCheck, BookOpen, CarFront, Check, CheckCircle2,
  CircleHelp, ClipboardCheck, GraduationCap, ListChecks, MapPin, MessageCircle,
  PartyPopper, RotateCcw, Send, Sparkles, Trophy, UserRound, X
} from 'lucide-react';
import './training.css';

const STEPS = [
  ['Olá', 'Inicie a conversa'],
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
    'Envie “Olá” para iniciar o atendimento simulado.',
    'Escolha o Tour que está disponível para a sua Ola.',
    'Depois de selecionar o Tour, confirme “Solicitar carrinho”.',
    'O motorista assume o Tour e deixa o grupo na Casa.',
    'Na Casa, use a opção para solicitar o próximo carrinho até a Galeria.',
    'Escolha o destino do grupo antes de solicitar o carrinho final.',
    `Revise: ${tour?.label || 'Tour'} → Casa → Galeria → ${destination?.name || 'destino'}.`
  ];
  return hints[step] || hints[0];
}

function Progress({ step }) {
  return <ol className="training-progress" aria-label="Etapas do treinamento">{STEPS.map(([label], index) => <li key={label} className={index <= step ? 'done' : ''}><span>{index < step ? <Check size={12} /> : index + 1}</span><small>{label}</small></li>)}</ol>;
}

function Bubble({ children, mine = false, muted = false }) {
  return <div className={`chat-bubble ${mine ? 'mine' : ''} ${muted ? 'muted' : ''}`}>{children}</div>;
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
  const destinationRequest = step >= 6 && destination;

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

  function beginConversation() {
    setStep(1);
    setShowTourPicker(true);
  }

  function chooseTour(item) {
    setTour(item);
    setShowTourPicker(false);
    setStep(2);
  }

  function requestFirstCart() {
    setStep(3);
  }

  function chooseDestination(item) {
    setDestination(item);
    setShowDestinationPicker(false);
    setStep(5);
  }

  function requestDestinationCart() {
    setStep(6);
  }

  if (!started) {
    return <main className="training-welcome">
      <section className="welcome-card">
        <div className="welcome-lock"><BadgeCheck size={18} /> Link privado de treinamento</div>
        <div className="welcome-icon"><CarFront size={42} /></div>
        <p className="eyebrow">THE CLUB · CARRINHOS</p>
        <h1>Simulador de treinamento</h1>
        <p className="welcome-copy">Aprenda na prática a solicitar um carrinho, passar pela Casa, acompanhar a Galeria e escolher o destino final.</p>
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
          <Bubble mine>Olá <small>agora</small></Bubble>
          {step >= 1 && <Bubble>Olá, {firstName}. Há 3 Tour(es) disponível(is). Escolha o seu Tour para solicitar o carrinho no Prestige.</Bubble>}
          {tour && <Bubble mine>{tour.label}<small>{tour.wave} · disponível</small></Bubble>}
          {step >= 2 && tour && <Bubble>{tour.label} selecionado. Confirme para solicitar o carrinho no Prestige.</Bubble>}
          {step >= 3 && tour && <Bubble mine>Solicitar carrinho</Bubble>}
          {step >= 3 && tour && <Bubble>Solicitação enviada: {tour.label} em Prestige Selection. Aguarde um motorista assumir.</Bubble>}
          {step >= 3 && tour && <Bubble>Motorista Lucas assumiu {tour.label}. O atendimento está em andamento.</Bubble>}
          {step >= 3 && tour && <Bubble>{tour.label} chegou à Casa. Solicite um carrinho quando o grupo precisar seguir para a Galeria.</Bubble>}
          {step >= 4 && tour && <Bubble mine>Solicitar na Casa</Bubble>}
          {step >= 4 && tour && <Bubble>Solicitação enviada: {tour.label} na Casa. O motorista está levando o grupo para a Galeria.</Bubble>}
          {step >= 4 && tour && <Bubble>{tour.label} chegou à Galeria. Escolha o destino para solicitar um carrinho.</Bubble>}
          {destination && <Bubble mine>{destination.name}<small>Solicitar carrinho</small></Bubble>}
          {destinationRequest && <Bubble>Solicitação enviada: {tour.label} da Galeria para {destination.name}. Aguarde um motorista assumir.</Bubble>}
          {finished && destination && <Bubble>Motorista Lucas assumiu {tour.label}. Tour finalizado com sucesso. Obrigado!</Bubble>}
        </div>
        <div className="chat-actions">
          {step === 0 && <button type="button" onClick={beginConversation}><MessageCircle size={18} /> Enviar “Olá”</button>}
          {step === 1 && <button type="button" onClick={() => setShowTourPicker(true)}><ListChecks size={18} /> Escolher Tour</button>}
          {step === 2 && <button type="button" onClick={requestFirstCart}><ArrowRight size={18} /> Solicitar carrinho</button>}
          {step === 3 && <button type="button" onClick={() => setStep(4)}><CarFront size={18} /> Solicitar na Casa</button>}
          {step === 4 && <button type="button" onClick={() => setShowDestinationPicker(true)}><ListChecks size={18} /> Escolher destino</button>}
          {step === 5 && destination && <button type="button" onClick={requestDestinationCart}><ArrowRight size={18} /> Solicitar carrinho</button>}
        </div>
      </div>
      {guided && !finished && <aside className="training-hint"><Sparkles size={23} /><div><strong>Passo {Math.min(step + 1, STEPS.length)} de {STEPS.length}</strong><p>{hintFor(step, tour, destination)}</p></div></aside>}
      {finished && <aside className="training-complete"><PartyPopper size={30} /><div><strong>Treinamento concluído!</strong><p>Você completou o Tour simulado com sucesso.</p></div></aside>}
    </section>
    <footer className="training-footer"><span><Trophy size={17} /> Progresso: {Math.min(100, Math.round((step / (STEPS.length - 1)) * 100))}%</span><span>{tour?.label || 'Tour pendente'} {destination ? `· ${destination.name}` : ''}</span></footer>

    {showTourPicker && <div className="training-modal-backdrop" role="presentation"><section className="training-modal" role="dialog" aria-modal="true" aria-label="Escolher Tour"><button className="modal-close" type="button" onClick={() => setShowTourPicker(false)} aria-label="Fechar"><X size={21} /></button><h2>Escolher Tour</h2><p>Selecione o Tour disponível para esta simulação.</p><div className="choice-list">{TOURS.map((item) => <button key={item.id} type="button" onClick={() => chooseTour(item)}><span className="choice-icon"><UserRound size={18} /></span><span><strong>{item.label}</strong><small>{item.wave} · {item.state}</small></span><ArrowRight size={18} /></button>)}</div></section></div>}
    {showDestinationPicker && <div className="training-modal-backdrop" role="presentation"><section className="training-modal" role="dialog" aria-modal="true" aria-label="Escolher destino"><button className="modal-close" type="button" onClick={() => setShowDestinationPicker(false)} aria-label="Fechar"><X size={21} /></button><h2>Escolher destino</h2><p>Selecione para onde o grupo seguirá saindo da Galeria.</p><div className="choice-list">{DESTINATIONS.map((item) => <button key={item.id} type="button" onClick={() => chooseDestination(item)}><span className="choice-icon destination"><MapPin size={18} /></span><span><strong>{item.name}</strong><small>{item.type} · Solicitar carrinho</small></span><ArrowRight size={18} /></button>)}</div></section></div>}
  </main>;
}

createRoot(document.getElementById('root')).render(<App />);

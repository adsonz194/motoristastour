import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  BarChart3, Bell, Building2, CalendarDays, CarFront, Check, ChevronRight, CircleUserRound,
  Clock3, FileClock, Flag, House, Image, LayoutDashboard, LoaderCircle, LockKeyhole,
  LogOut, MapPin, Menu, MoreHorizontal, Plus, Route, Settings, ShieldCheck, ShoppingCart,
  Star, UserCog, UserRound, Users, X
} from 'lucide-react';
import './styles.css';

const STATUS = {
  DISPONIVEL: { label: 'Disponível', tone: 'teal' },
  EM_TOUR: { label: 'Em percurso', tone: 'blue' },
  NA_CASA: { label: 'Na Casa', tone: 'orange' },
  AGUARDANDO_CASA: { label: 'Aguardando na Casa', tone: 'orange' },
  NA_GALERIA: { label: 'Na Galeria', tone: 'purple' },
  EM_APRESENTACAO: { label: 'Em apresentação', tone: 'purple' },
  AGUARDANDO_DESTINO: { label: 'Aguardando destino', tone: 'green' },
  EM_DESTINO_FINAL: { label: 'Em destino final', tone: 'blue' },
  CONCLUIDO: { label: 'Concluído', tone: 'gray' },
  DESISTENCIA: { label: 'Desistência', tone: 'gray' }
};

const DRIVER_STATUS = {
  DISPONIVEL: { label: 'Disponível', tone: 'green' },
  EM_TOUR: { label: 'Em tour', tone: 'blue' },
  A_CAMINHO_GALERIA: { label: 'A caminho da Galeria', tone: 'blue' },
  CASA: { label: 'Na Casa', tone: 'orange' },
  GALERIA: { label: 'Na Galeria', tone: 'purple' },
  DESTINO_FINAL: { label: 'Destino final', tone: 'teal' },
  APOIO_HOSTESS: { label: 'Em apoio à Hostess', tone: 'purple' },
  FOLGA: { label: 'Folga', tone: 'gray' },
  ATESTADO: { label: 'Atestado', tone: 'orange' }
};

const WAVES = {
  WAVE_1: { label: '1ª Ola', tourTime: '09:00', transferTime: '07:50' },
  WAVE_2: { label: '2ª Ola', tourTime: '11:00', transferTime: '09:50' }
};

const TRANSFER_STATUS = {
  AGENDADO: { label: 'Agendado', tone: 'teal' },
  EM_DESLOCAMENTO: { label: 'Em deslocamento', tone: 'blue' },
  CHEGOU_PRESTIGE: { label: 'Chegou ao Praia do Forte', tone: 'green' },
  DESISTENCIA: { label: 'Desistência', tone: 'gray' }
};

const NAV = [
  { id: 'dashboard', label: 'Painel Geral', icon: LayoutDashboard },
  { id: 'prestige', label: 'Prestige Praia do Forte', icon: Building2 },
  { id: 'transfers', label: 'Convites Waves → Praia', icon: Route },
  { id: 'tours', label: 'Tours em Andamento', icon: Route },
  { id: 'gallery', label: 'Galeria', icon: Image },
  { id: 'home', label: 'Casa (Aguardando)', icon: House },
  { id: 'destinations', label: 'Destinos Finais', icon: MapPin },
  { id: 'consultants', label: 'Consultores', icon: UserRound },
  { id: 'drivers', label: 'Motoristas', icon: CarFront },
  { id: 'carts', label: 'Carrinhos', icon: ShoppingCart },
  { id: 'history', label: 'Histórico', icon: FileClock },
  { id: 'reports', label: 'Relatórios', icon: BarChart3 },
  { id: 'settings', label: 'Configurações', icon: Settings, admin: true }
];

const DRIVER_NAV_IDS = new Set(['dashboard', 'prestige', 'tours', 'gallery', 'home', 'destinations', 'drivers']);

// The server is the authority for access. These definitions only keep the UI
// understandable while an older deployment is still returning role-only users.
const FALLBACK_PERMISSION_CATALOG = [
  { code: 'VIEW_DASHBOARD', label: 'Ver Painel Geral', description: 'Apenas visualiza o Painel Geral. Não libera botões, alteração de rota ou cadastros.', group: 'Visualização' },
  { code: 'VIEW_PRESTIGE', label: 'Ver Prestige', description: 'Visualiza os grupos disponíveis no Prestige.', group: 'Visualização' },
  { code: 'VIEW_TOURS', label: 'Ver tours em andamento', description: 'Visualiza o andamento dos tours.', group: 'Visualização' },
  { code: 'VIEW_GALLERY', label: 'Ver Galeria', description: 'Visualiza grupos na Galeria.', group: 'Visualização' },
  { code: 'VIEW_HOME', label: 'Ver Casa', description: 'Visualiza grupos que aguardam na Casa.', group: 'Visualização' },
  { code: 'VIEW_DESTINATIONS', label: 'Ver destinos finais', description: 'Visualiza os destinos finais dos grupos.', group: 'Visualização' },
  { code: 'VIEW_TRANSFERS', label: 'Ver convites Waves', description: 'Visualiza os convites e traslados Waves.', group: 'Visualização' },
  { code: 'VIEW_DRIVERS', label: 'Ver motoristas', description: 'Visualiza status e disponibilidade dos motoristas.', group: 'Visualização' },
  { code: 'VIEW_CONSULTANTS', label: 'Ver consultores', description: 'Visualiza os consultores cadastrados.', group: 'Visualização' },
  { code: 'VIEW_CARTS', label: 'Ver carrinhos', description: 'Visualiza os carrinhos cadastrados.', group: 'Visualização' },
  { code: 'VIEW_HISTORY', label: 'Ver histórico', description: 'Visualiza o histórico e a auditoria da operação.', group: 'Visualização' },
  { code: 'VIEW_REPORTS', label: 'Ver relatórios', description: 'Visualiza os indicadores e relatórios.', group: 'Visualização' },
  { code: 'CHECK_IN', label: 'Fazer check-in', description: 'Registra presença de trabalho no dia.', group: 'Operação' },
  { code: 'MANAGE_TOUR_QUANTITIES', label: 'Registrar quantidades de tours', description: 'Registra as quantidades de tours e Self Gen por Ola.', group: 'Operação' },
  { code: 'MANAGE_TOURS', label: 'Operar tours', description: 'Inicia tours e atualiza etapas, rotas e destinos.', group: 'Operação' },
  { code: 'MANAGE_TRANSFERS', label: 'Gerenciar convites Waves', description: 'Cadastra, atualiza e registra desistências dos convites Waves.', group: 'Operação' },
  { code: 'REQUEST_HOSTESS_CAR', label: 'Solicitar carro para Hostess', description: 'Abre e encerra solicitação de carro para a Hostess.', group: 'Operação' },
  { code: 'MANAGE_HOSTESS_SUPPORT', label: 'Atender chamado da Hostess', description: 'Permite assumir e encerrar apoio a uma solicitação da Hostess.', group: 'Operação' },
  { code: 'MANAGE_DRIVERS', label: 'Gerenciar motoristas', description: 'Cria, edita e exclui motoristas.', group: 'Cadastros e administração' },
  { code: 'MANAGE_CONSULTANTS', label: 'Gerenciar consultores', description: 'Cria, edita e exclui consultores.', group: 'Cadastros e administração' },
  { code: 'MANAGE_USERS', label: 'Gerenciar usuários', description: 'Cria, altera permissões e exclui usuários.', group: 'Cadastros e administração' },
  { code: 'MANAGE_SETTINGS', label: 'Gerenciar configurações', description: 'Altera o Prestige de saída, fechamentos e zera a operação.', group: 'Cadastros e administração' }
];

const ROLE_DEFAULT_PERMISSIONS = {
  ADMIN: FALLBACK_PERMISSION_CATALOG.map((item) => item.code),
  MOTORISTA: ['VIEW_DASHBOARD', 'VIEW_PRESTIGE', 'VIEW_TOURS', 'VIEW_GALLERY', 'VIEW_HOME', 'VIEW_DESTINATIONS', 'VIEW_DRIVERS', 'CHECK_IN', 'MANAGE_TOURS', 'MANAGE_HOSTESS_SUPPORT'],
  HOSTESS: ['VIEW_DASHBOARD', 'CHECK_IN', 'MANAGE_TOUR_QUANTITIES', 'REQUEST_HOSTESS_CAR'],
  CONCIERGE: ['VIEW_TRANSFERS', 'MANAGE_TRANSFERS'],
  VISUALIZADOR: ['VIEW_DASHBOARD']
};

function normalizedPermissionCode(value) {
  return String(value || '').trim().toUpperCase().replace(/[^A-Z0-9]+/g, '_').replace(/^_|_$/g, '');
}

function compactPermissionCode(value) {
  return normalizedPermissionCode(value).replace(/_/g, '');
}

function permissionCodes(value) {
  if (value === undefined || value === null) return [];
  if (Array.isArray(value)) return value.flatMap((item) => permissionCodes(item));
  if (typeof value === 'string') return [normalizedPermissionCode(value)].filter(Boolean);
  if (typeof value === 'object') {
    const directCode = value.code || value.id || value.permission || value.name;
    if (directCode) return [normalizedPermissionCode(directCode)].filter(Boolean);
    return Object.entries(value).flatMap(([key, enabled]) => enabled ? [normalizedPermissionCode(key)] : []);
  }
  return [];
}

function hasPermissionModel(user) {
  return Boolean(user && ['effectivePermissions', 'permissions', 'capabilities'].some((key) => Object.prototype.hasOwnProperty.call(user, key)));
}

function effectivePermissionCodes(user) {
  if (!user) return [];
  if (Object.prototype.hasOwnProperty.call(user, 'effectivePermissions')) return permissionCodes(user.effectivePermissions);
  if (Object.prototype.hasOwnProperty.call(user, 'capabilities')) return permissionCodes(user.capabilities);
  return permissionCodes(user.permissions);
}

function legacyCan(user, permission) {
  const role = user?.role;
  if (role === 'ADMIN') return true;
  if (permission === 'VIEW_DASHBOARD') return ['MOTORISTA', 'HOSTESS'].includes(role);
  if (['VIEW_PRESTIGE', 'VIEW_TOURS', 'VIEW_GALLERY', 'VIEW_HOME', 'VIEW_DESTINATIONS', 'VIEW_DRIVERS'].includes(permission)) return role === 'MOTORISTA';
  if (permission === 'VIEW_TRANSFERS') return role === 'CONCIERGE';
  if (permission === 'CHECK_IN') return ['MOTORISTA', 'HOSTESS'].includes(role);
  if (permission === 'MANAGE_TOUR_QUANTITIES' || permission === 'REQUEST_HOSTESS_CAR') return role === 'HOSTESS';
  if (permission === 'MANAGE_TOURS' || permission === 'MANAGE_HOSTESS_SUPPORT') return role === 'MOTORISTA';
  if (permission === 'MANAGE_TRANSFERS') return role === 'CONCIERGE';
  return false;
}

function can(user, permission) {
  const wanted = normalizedPermissionCode(permission);
  if (!wanted) return false;
  if (!hasPermissionModel(user)) return legacyCan(user, wanted);
  const granted = effectivePermissionCodes(user);
  const wantedCompact = compactPermissionCode(wanted);
  return granted.some((item) => {
    const code = normalizedPermissionCode(item);
    return code === '*' || code === wanted || compactPermissionCode(code) === wantedCompact;
  });
}

function canAny(user, permissions) {
  return permissions.some((permission) => can(user, permission));
}

function canAccessPage(user, page) {
  const permissions = {
    dashboard: ['VIEW_DASHBOARD'],
    prestige: ['VIEW_PRESTIGE', 'MANAGE_TOURS'],
    tours: ['VIEW_TOURS', 'MANAGE_TOURS'],
    gallery: ['VIEW_GALLERY', 'MANAGE_TOURS'],
    home: ['VIEW_HOME', 'MANAGE_TOURS'],
    destinations: ['VIEW_DESTINATIONS', 'MANAGE_TOURS'],
    transfers: ['VIEW_TRANSFERS', 'MANAGE_TRANSFERS'],
    drivers: ['VIEW_DRIVERS', 'MANAGE_DRIVERS'],
    consultants: ['VIEW_CONSULTANTS', 'MANAGE_CONSULTANTS'],
    carts: ['VIEW_CARTS'],
    history: ['VIEW_HISTORY'],
    reports: ['VIEW_REPORTS'],
    settings: ['MANAGE_USERS', 'MANAGE_SETTINGS']
  };
  return canAny(user, permissions[page] || []);
}

function firstAccessiblePage(user) {
  return NAV.find((item) => canAccessPage(user, item.id))?.id || '';
}

function permissionCatalog(dataOrCatalog) {
  const source = Array.isArray(dataOrCatalog)
    ? dataOrCatalog
    : dataOrCatalog?.permissionCatalog || dataOrCatalog?.permissionsCatalog || dataOrCatalog?.access?.permissionCatalog || [];
  const fallbackByCode = new Map(FALLBACK_PERMISSION_CATALOG.map((item) => [item.code, item]));
  const entries = (Array.isArray(source) ? source : []).map((item) => {
    const code = normalizedPermissionCode(typeof item === 'string' ? item : item?.code || item?.key || item?.id || item?.permission);
    if (!code) return null;
    const fallback = fallbackByCode.get(code) || {};
    return {
      code,
      label: item?.label || item?.name || fallback.label || code.replace(/_/g, ' '),
      description: item?.description || fallback.description || 'Permite acessar esta função.',
      group: item?.group || item?.category || fallback.group || 'Outras permissões'
    };
  }).filter(Boolean);
  return entries.length ? entries : FALLBACK_PERMISSION_CATALOG;
}

function defaultPermissionsForRole(role, catalog = FALLBACK_PERMISSION_CATALOG) {
  const validCodes = new Set(catalog.map((item) => normalizedPermissionCode(item.code)));
  return (ROLE_DEFAULT_PERMISSIONS[role] || []).filter((code) => validCodes.has(code));
}

function accountPermissions(account) {
  if (!account) return null;
  if (Object.prototype.hasOwnProperty.call(account, 'permissions')) return permissionCodes(account.permissions);
  if (Object.prototype.hasOwnProperty.call(account, 'effectivePermissions')) return permissionCodes(account.effectivePermissions);
  return null;
}

const actionMeta = {
  start: { title: 'Iniciar tour', text: 'Selecione os motoristas para registrar a saída do Prestige. Um carrinho disponível será reservado automaticamente para cada motorista.', label: 'Iniciar tour', allocations: true },
  withdraw: { title: 'Registrar desistência', text: 'Confirme que este tour foi cancelado antes da saída. Ele sairá da lista de disponíveis, continuará registrado no histórico e não poderá ser iniciado.', label: 'Desistência', danger: true },
  'arrived-home': { title: 'Registrar situação na Casa', text: 'Cada motorista registra se deixou o grupo ou se permaneceu aguardando na Casa.', label: 'Registrar Casa', individualArrival: true },
  'return-prestige': { title: 'Trocar motoristas da Casa', text: 'Libere a equipe deste casal para atender outra família. Este casal ficará aguardando na Casa até que a nova equipe completa seja selecionada.', label: 'Liberar e trocar' },
  'pickup-home': { title: 'Buscar grupo na Casa', text: 'Selecione os motoristas. Um carrinho disponível será reservado automaticamente para cada motorista. Esta busca não soma saída de tour.', label: 'Buscar na Casa', allocations: true },
  'depart-home': { title: 'Seguir para a Galeria', text: 'Todos os carrinhos necessários já estão na Casa. Confirme a saída do grupo para a Galeria.', label: 'Seguir para Galeria' },
  'correct-to-home': { title: 'Corrigir status do tour', text: 'Use somente se a saída para a Galeria foi marcada por engano. O grupo e os motoristas voltarão a constar como estando na Casa.', label: 'Corrigir: ainda estou na Casa' },
  'join-home': { title: 'Chamar motorista para a Casa', text: 'Este grupo precisa de outro motorista para usar todos os carrinhos necessários até a Galeria.', label: 'Chamar motorista', allocations: true, homeJoin: true },
  'deliver-gallery': { title: 'Entregar na Galeria', text: 'Confirme a chegada à Galeria. O grupo seguirá diretamente para a fila de destino final.', label: 'Entregar na Galeria' },
  'assign-destination': { title: 'Levar ao destino final', text: 'Selecione o destino e os motoristas disponíveis. Um carrinho será reservado automaticamente para cada motorista.', label: 'Levar ao destino', allocations: true, destination: true },
  'change-destination': { title: 'Alterar destino final', text: 'Corrija o destino escolhido sem alterar os motoristas, carrinhos ou o status do tour.', label: 'Alterar destino', destination: true },
  'complete-destination': { title: 'Encerrar no destino final', text: 'Confirme a chegada ao destino. O tour será encerrado e os motoristas ficarão disponíveis.', label: 'Encerrar tour' }
};

function classNames(...values) {
  return values.filter(Boolean).join(' ');
}

function initials(name = '') {
  return name.split(' ').filter(Boolean).slice(0, 2).map((word) => word[0]).join('').toUpperCase() || 'TI';
}

function time(value) {
  if (!value) return '—';
  return new Intl.DateTimeFormat('pt-BR', { hour: '2-digit', minute: '2-digit' }).format(new Date(value));
}

function dateLabel() {
  return new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' }).format(new Date());
}

function activityDateLabel(value) {
  const parsed = new Date(value);
  if (!value || Number.isNaN(parsed.getTime())) return 'Data não informada';
  return new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' }).format(parsed);
}

function firstAuditValue(audit, ...keys) {
  return keys.map((key) => audit?.[key]).find((value) => value !== undefined && value !== null && value !== '' && (!Array.isArray(value) || value.length > 0));
}

function auditText(value, fallback = 'Não informado') {
  const items = Array.isArray(value) ? value : [value];
  const text = items.map((item) => {
    if (item && typeof item === 'object') return item.name || item.label || item.username || '';
    return item;
  }).filter(Boolean).join(', ');
  return text || fallback;
}

function roleLabel(role) {
  return ({ ADMIN: 'Administrador', MOTORISTA: 'Motorista', HOSTESS: 'Hostess', CONCIERGE: 'Concierge', VISUALIZADOR: 'Somente visualização' })[role] || role || '';
}

function urlBase64ToUint8Array(value) {
  const padding = '='.repeat((4 - (value.length % 4)) % 4);
  const base64 = `${value}${padding}`.replace(/-/g, '+').replace(/_/g, '/');
  const raw = window.atob(base64);
  return Uint8Array.from(raw, (character) => character.charCodeAt(0));
}

function api(token, path, options = {}) {
  return fetch(path, {
    ...options,
    headers: {
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {})
    }
  }).then(async (response) => {
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.error || 'Não foi possível concluir a ação.');
    return payload;
  });
}

function Logo() {
  return <div className="brand"><span className="brand-star"><Star size={27} fill="currentColor" /></span><span><strong>IBEROSTAR</strong><small>TOUR INTERNO</small></span></div>;
}

function StatusPill({ status, driver = false }) {
  const meta = (driver ? DRIVER_STATUS : STATUS)[status] || { label: status, tone: 'gray' };
  return <span className={classNames('status-pill', `tone-${meta.tone}`)}>{meta.label}</span>;
}

function TransferStatusPill({ status }) {
  const meta = TRANSFER_STATUS[status] || { label: status, tone: 'gray' };
  return <span className={classNames('status-pill', `tone-${meta.tone}`)}>{meta.label}</span>;
}

function Avatar({ name, color = 'blue' }) {
  return <span className={classNames('avatar', `avatar-${color}`)}>{initials(name)}</span>;
}

function Login({ onLogin }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setError(''); setLoading(true);
    try {
      const result = await api('', '/api/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) });
      onLogin(result.token, result.user);
    } catch (err) {
      setError(err.message);
    } finally { setLoading(false); }
  }

  return <main className="login-page">
    <section className="login-brand-panel"><Logo /><div className="login-illustration"><div className="orbit orbit-a" /><div className="orbit orbit-b" /><Route size={54} /><h1>Tour interno,<br />operação sob controle.</h1><p>Acompanhe cada família do Prestige ao destino final em tempo real.</p></div><p className="login-footer">Iberostar Tour Interno · Painel operacional</p></section>
    <section className="login-form-panel"><form className="login-card" onSubmit={submit}><div className="login-kicker"><ShieldCheck size={18} /> Acesso seguro</div><h2>Bem-vindo</h2><p>Entre com suas credenciais para acessar o painel.</p>
      <label>Usuário<input autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} placeholder="Seu usuário" required /></label>
      <label>Senha<input type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Sua senha" required /></label>
      {error && <div className="form-error">{error}</div>}
      <button className="button button-primary login-submit" disabled={loading}>{loading ? <LoaderCircle className="spin" size={18} /> : <LockKeyhole size={18} />} Entrar no painel</button>
      <a className="public-panel-link" href="/consultores"><CarFront size={16} /> Painel público dos consultores</a>
    </form></section>
  </main>;
}

function availableNavItems(user, operationSettings) {
  return NAV.filter((item) => {
    if (!canAccessPage(user, item.id)) return false;
    if (item.id === 'transfers' && user.role === 'CONCIERGE' && operationSettings?.conciergePanelClosed) return false;
    return true;
  });
}

function Sidebar({ user, page, setPage, signOut, open, setOpen, operationSettings }) {
  const departureLabel = operationSettings?.departureLabel || 'Prestige Waves Bahia';
  const nav = availableNavItems(user, operationSettings);
  return <aside className={classNames('sidebar', open && 'sidebar-open')}>
    <div className="sidebar-top"><Logo /><button className="sidebar-close" onClick={() => setOpen(false)} aria-label="Fechar menu"><X /></button></div>
    <nav>{nav.map(({ id, label, icon: Icon }) => <button key={id} onClick={() => { setPage(id); setOpen(false); }} className={classNames('nav-item', page === id && 'nav-active')}><Icon size={19} /><span>{id === 'prestige' ? departureLabel : label}</span></button>)}</nav>
    <button className="nav-item nav-exit" onClick={signOut}><LogOut size={19} /><span>Sair</span></button>
  </aside>;
}

function MobileNav({ page, setPage, user, operationSettings }) {
  const permitted = availableNavItems(user, operationSettings);
  const items = permitted.slice(0, 4);
  const showMore = permitted.length > items.length && canAccessPage(user, 'settings');
  const departureLabel = operationSettings?.departureLabel || 'Prestige Waves Bahia';
  const count = Math.max(1, items.length + (showMore ? 1 : 0));
  if (!items.length && !showMore) return null;
  return <nav className={classNames('mobile-nav', count === 1 && 'mobile-nav-single')} style={{ gridTemplateColumns: `repeat(${count}, 1fr)` }}>{items.map(({ id, label, icon: Icon }) => { const itemLabel = id === 'prestige' ? departureLabel : label; return <button key={id} className={page === id ? 'active' : ''} onClick={() => setPage(id)}><Icon size={20} /><span>{id === 'dashboard' ? 'Painel' : id === 'prestige' ? departureLabel.includes('Selection') ? 'Selection' : 'Bahia' : itemLabel.split(' ')[0]}</span></button>; })}{showMore && <button onClick={() => setPage('settings')} className={page === 'settings' ? 'active' : ''}><MoreHorizontal size={20} /><span>Mais</span></button>}</nav>;
}

function Topbar({ user, setMenuOpen, notificationPermission, onNotifications }) {
  const [clock, setClock] = useState(time(new Date()));
  useEffect(() => { const timer = setInterval(() => setClock(time(new Date())), 30000); return () => clearInterval(timer); }, []);
  const role = roleLabel(user.role);
  const notificationLabel = notificationPermission === 'granted' ? 'Notificações push ativas. Toque para enviar um teste.' : notificationPermission === 'denied' ? 'Notificações bloqueadas no navegador.' : 'Ativar notificações push neste aparelho';
  return <header className="topbar"><button className="menu-button" onClick={() => setMenuOpen(true)} aria-label="Abrir menu"><Menu size={29} /></button><div className="topbar-spacer" /><div className="topbar-date"><CalendarDays size={18} /><span>{dateLabel()}</span></div><div className="topbar-date"><Clock3 size={18} /><span>{clock}</span></div><button className={classNames('bell', notificationPermission === 'granted' && 'bell-enabled')} onClick={onNotifications} aria-label={notificationLabel} title={notificationLabel}><Bell size={20} /><span className="bell-status" aria-hidden="true" /></button><div className="user-menu"><CircleUserRound size={25} /><div><strong>{user.name}</strong><span>{role}</span></div><ChevronRight size={16} /></div></header>;
}

function MetricCard({ icon: Icon, color, title, count, sub }) {
  return <article className="metric-card"><div className={classNames('metric-icon', `metric-${color}`)}><Icon size={29} /></div><div className="metric-copy"><small>{title}</small><div><strong>{count}</strong><span>{sub}</span></div></div></article>;
}

function TourTable({ tours, data, user, onAction, compact = false, empty = 'Nenhum grupo nesta etapa.' }) {
  const toursClosed = Boolean(data.operationSettings?.toursClosed);
  const consultant = (tour) => tour.consultantName || data.consultants.find((item) => item.id === tour.consultantId)?.name || 'Sem consultor';
  const driverDetails = (tour) => {
    const names = (items) => items.map((item) => data.drivers.find((driver) => driver.id === item.driverId)?.name).filter(Boolean).join(', ') || '—';
    if (tour.status !== 'NA_CASA') return { active: names(tour.allocations || []), returned: '', cartsAtHome: tour.requiredCartCount || (tour.allocations || []).length };
    const staying = (tour.allocations || []).filter((item) => item.homeDecision === 'AGUARDOU_NA_CASA');
    const returned = (tour.allocations || []).filter((item) => item.homeDecision === 'DEIXOU_NA_CASA');
    return { active: names(staying), returned: names(returned), cartsAtHome: staying.length };
  };
  const actionFor = (tour) => {
    if (tour.status === 'DISPONIVEL') return toursClosed ? null : 'start';
    if (tour.status === 'EM_TOUR') return tour.phase === 'Casa → Galeria' ? 'deliver-gallery' : 'arrived-home';
    if (tour.status === 'NA_CASA') {
      const requiredCarts = tour.requiredCartCount || (tour.allocations || []).length;
      const driversAtHome = (tour.allocations || []).filter((item) => item.homeDecision === 'AGUARDOU_NA_CASA').length;
      return driversAtHome < requiredCarts ? 'join-home' : 'depart-home';
    }
    if (tour.status === 'AGUARDANDO_CASA') return 'pickup-home';
    if (tour.status === 'AGUARDANDO_DESTINO') return 'assign-destination';
    if (tour.status === 'EM_DESTINO_FINAL') return 'complete-destination';
    return null;
  };
  if (!tours.length) return <div className="empty-state">{empty}</div>;
  return <div className={classNames('table-wrap', 'tour-table', compact && 'table-compact')}><table><thead><tr><th>Consultor</th><th>Família / Casal</th><th>Pessoas</th><th>Carrinhos</th><th>Motoristas</th><th>Status</th><th aria-label="Ações" /></tr></thead><tbody>{tours.map((tour) => {
    const action = actionFor(tour); const consultantName = consultant(tour); const driverInfo = driverDetails(tour);
    // A permissão operacional vale para toda a equipe autorizada: um motorista
    // pode assumir ou corrigir qualquer tour. O servidor registra quem fez cada alteração.
    // VIEW_DASHBOARD, por sua vez, continua estritamente em modo de visualização.
    const canOperate = can(user, 'MANAGE_TOURS');
    const team = consultantName !== 'Sem consultor' && driverInfo.active !== '—' ? `${consultantName} com ${driverInfo.active}` : '';
    const isOnInitialRoute = tour.status === 'EM_TOUR' && tour.phase !== 'Casa → Galeria' && !(tour.allocations || []).some((allocation) => allocation.homeDecision);
    const canCorrectToHome = tour.status === 'EM_TOUR' && tour.phase === 'Casa → Galeria';
    const canChangeDestination = tour.status === 'EM_DESTINO_FINAL';
    const canWithdraw = tour.status === 'DISPONIVEL';
    return <tr key={tour.id}><td><div className="name-cell"><Avatar name={consultantName} color="pink" /><span>{consultantName}</span></div></td><td><strong>{tour.groupName}</strong><small className="schedule-info">{WAVES[tour.wave]?.label || 'Ola não definida'} · {tour.scheduledTime || '—'}</small>{consultantName !== 'Sem consultor' && <small className="mobile-consultant">Consultor: {consultantName}</small>}{team && <small className="tour-team">{team}</small>}{tour.selfGuide && <small className="self-guide">Self Gen</small>}{tour.status === 'NA_CASA' && <div className="home-presence"><House size={14} /><span><b>NA CASA COM O CASAL:</b> {driverInfo.active}</span></div>}{tour.status === 'NA_CASA' && driverInfo.returned !== '—' && <small className="returned-driver">VOLTOU AO PRESTIGE: {driverInfo.returned}</small>}</td><td>{tour.people || '—'}</td><td>{driverInfo.cartsAtHome || '—'}</td><td><strong>{driverInfo.active}</strong>{driverInfo.returned && driverInfo.returned !== '—' && <small className="schedule-info">Retornou ao Prestige: {driverInfo.returned}</small>}</td><td><StatusPill status={tour.status} /></td><td className="actions-cell">{canOperate && isOnInitialRoute && <button className="mini-action secondary" onClick={() => onAction(tour, 'deliver-gallery')}>Chegou direto à Galeria</button>}{canOperate && canCorrectToHome && <button className="mini-action secondary" onClick={() => onAction(tour, 'correct-to-home')}>{actionMeta['correct-to-home'].label}</button>}{canOperate && tour.status === 'NA_CASA' && <button className="mini-action secondary" onClick={() => onAction(tour, 'return-prestige')}>Trocar motoristas</button>}{canOperate && canChangeDestination && <button className="mini-action secondary" onClick={() => onAction(tour, 'change-destination')}>{actionMeta['change-destination'].label}</button>}{canOperate && canWithdraw && <button className="mini-action danger-mini" onClick={() => onAction(tour, 'withdraw')}>Desistência</button>}{canOperate && action && <button className="mini-action" onClick={() => onAction(tour, action)}>{actionMeta[action].label}</button>}</td></tr>;
  })}</tbody></table></div>;
}

function TransferTable({ transfers, onAction, user, settings = {}, empty = 'Nenhum convite agendado para hoje.' }) {
  if (!transfers.length) return <div className="empty-state">{empty}</div>;
  return <div className="table-wrap transfer-table"><table><thead><tr><th>Horário</th><th>Ola do tour</th><th>Grupo / Convidados</th><th>Pessoas</th><th>Concierge</th><th>Trajeto</th><th>Status</th><th aria-label="Ações" /></tr></thead><tbody>{transfers.map((transfer) => {
    const canManageTransfers = can(user, 'MANAGE_TRANSFERS');
    const next = canManageTransfers && user?.role !== 'CONCIERGE' ? transfer.status === 'AGENDADO' ? settings.conciergePanelClosed ? null : 'start' : transfer.status === 'EM_DESLOCAMENTO' ? 'arrive' : null : null;
    const canWithdraw = canManageTransfers && transfer.status === 'AGENDADO' && (user?.role === 'CONCIERGE' || user?.role === 'ADMIN');
    return <tr key={transfer.id}><td><strong>{transfer.scheduledTime}</strong></td><td><span className="wave-badge">{WAVES[transfer.wave]?.label || transfer.wave}<small>Tour {transfer.tourStartTime}</small></span></td><td><strong>{transfer.groupName}</strong></td><td>{transfer.people}</td><td>{transfer.conciergeName}</td><td><span className="route-copy">Waves Bahia <ChevronRight size={13} /> Praia do Forte</span></td><td><TransferStatusPill status={transfer.status} /></td><td className="actions-cell">{next && <button className="mini-action" onClick={() => onAction(transfer, next)}>{next === 'start' ? 'Iniciar traslado' : 'Confirmar chegada'}</button>}{canWithdraw && <button className="mini-action danger-mini" onClick={() => onAction(transfer, 'withdraw')}>Desistência</button>}</td></tr>;
  })}</tbody></table></div>;
}

function DriverCard({ driver }) {
  return <article className="driver-card"><div className="driver-heading"><Avatar name={driver.name} color="photo" /><div><strong>{driver.name}</strong><span>Operação interna</span></div></div><StatusPill driver status={driver.status} />{driver.hostessAvailable && <span className="hostess-ready"><Check size={13} /> Reservado para a Hostess</span>}<div className="driver-stats"><span><small>Tours hoje</small><strong>{driver.toursStarted}</strong></span><span><small>Buscas Casa</small><strong>{driver.homePickups}</strong></span></div></article>;
}

function OperationRestriction({ settings }) {
  if (!settings || (!settings.toursClosed && !settings.conciergePanelClosed)) return null;
  const restrictions = [];
  if (settings.conciergePanelClosed) restrictions.push('Percurso Waves e painel do Concierge suspensos');
  if (settings.toursClosed) restrictions.push('Novas saídas de tour suspensas');
  return <section className="operation-restriction" role="status"><Building2 size={22} /><div><strong>Operação com hotel fechado</strong><span>{restrictions.join(' · ')}. Saída atual: {settings.departureLabel}.</span></div></section>;
}

function DriverHostessAvailability({ data, user, token, refresh, notify }) {
  const requests = (data.hostessRequests || []).filter((item) => item.status === 'SOLICITADO');
  const driver = (data.drivers || []).find((item) => item.id === user.driverId);
  const checkedIn = (data.attendance || []).some((item) => item.userId === user.id);
  const [saving, setSaving] = useState(false);
  const [requestId, setRequestId] = useState('');
  const unassignedRequests = requests.filter((item) => !item.assignedDriverId);
  const assignedRequest = requests.find((item) => item.id === driver?.hostessRequestId || item.assignedDriverId === driver?.id);
  const availableRequestIds = unassignedRequests.map((item) => item.id).join('|');
  useEffect(() => {
    setRequestId((current) => unassignedRequests.some((item) => item.id === current) ? current : (unassignedRequests[0]?.id || ''));
  }, [availableRequestIds]);
  if (!requests.length) return null;
  const canAnswer = checkedIn && driver?.active && driver?.status === 'DISPONIVEL' && !driver?.hostessAvailable && Boolean(requestId);
  const available = Boolean(driver?.hostessAvailable);
  async function setAvailability(nextAvailability) {
    setSaving(true);
    try {
      const result = await api(token, '/api/drivers/hostess-availability', { method: 'POST', body: JSON.stringify(nextAvailability ? { available: true, requestId } : { available: false }) });
      await refresh();
      notify(nextAvailability ? 'Você assumiu a solicitação da Hostess.' : result.request ? 'Seu apoio foi encerrado e a solicitação foi fechada.' : 'Seu apoio foi encerrado.', 'success');
    } catch (error) { notify(error.message, 'error'); } finally { setSaving(false); }
  }
  const requestLabel = (item) => `${item.requestedByName || 'Hostess'} · solicitado às ${time(item.createdAt)}`;
  return <section className="hostess-call driver-hostess-call"><div><span>CHAMADO DA HOSTESS</span><h2>{requests.length === 1 ? 'A Hostess solicitou um carro' : `${requests.length} solicitações de carro da Hostess`}</h2><p>{available ? `Você está atendendo ${assignedRequest?.requestedByName || 'esta solicitação'}. Ao encerrar seu apoio, essa solicitação também será encerrada.` : canAnswer ? 'Você está livre. Assuma um chamado para a Hostess saber quem irá buscá-la.' : unassignedRequests.length ? 'Faça check-in e fique disponível para responder a este chamado.' : 'Todos os chamados abertos já têm motorista em apoio.'}</p>{!available && unassignedRequests.length > 1 && <label className="hostess-request-picker">Qual solicitação você vai atender?<select value={requestId} onChange={(event) => setRequestId(event.target.value)}>{unassignedRequests.map((item) => <option value={item.id} key={item.id}>{requestLabel(item)}</option>)}</select></label>}</div>{available ? <button className="button button-secondary" onClick={() => setAvailability(false)} disabled={saving}>Encerrar apoio e solicitação</button> : <button className="button button-primary" onClick={() => setAvailability(true)} disabled={saving || !canAnswer}>{saving && <LoaderCircle className="spin" size={17} />} Assumir solicitação</button>}</section>;
}

function Flow({ counts }) {
  const stages = [['Prestige', counts.available.length], ['Em tour', counts.enTour.length], ['Casa', counts.home.length], ['Galeria', counts.gallery.length], ['Destino', counts.destination.length]];
  return <div className="flow"><Route size={18} /><div className="flow-line">{stages.map(([stage, count], index) => <React.Fragment key={stage}><div className={classNames('flow-stage', count > 0 && 'flow-active')}><span>{stage}</span><strong>{count}</strong></div>{index < stages.length - 1 && <ChevronRight size={16} />}</React.Fragment>)}</div></div>;
}

function CheckInCard({ data, user, token, refresh, notify }) {
  const [saving, setSaving] = useState(false);
  const attendance = (data.attendance || []).find((item) => item.userId === user.id);
  async function checkIn() {
    setSaving(true);
    try { await api(token, '/api/attendance/check-in', { method: 'POST' }); await refresh(); notify('Check-in registrado. Você está trabalhando hoje.', 'success'); } catch (error) { notify(error.message, 'error'); } finally { setSaving(false); }
  }
  const location = attendance?.location || user.checkInLocation || 'Prestige Praia do Forte';
  return <section className={classNames('checkin-card', attendance && 'checked-in')}><div><span>{attendance ? 'CHECK-IN CONFIRMADO' : 'SITUAÇÃO DE HOJE'}</span><h2>{attendance ? 'Você está trabalhando' : 'Folga ou atestado'}</h2><p>Local de check-in: <strong>{location}</strong>{attendance ? ` · confirmado às ${time(attendance.checkInAt)}.` : '.'}</p></div>{attendance ? <span className="checkin-done"><Check size={18} /> Em serviço</span> : <button className="button button-primary" onClick={checkIn} disabled={saving}>{saving && <LoaderCircle className="spin" size={17} />} Fazer check-in</button>}</section>;
}

function recentAuditActor(activity) {
  const audit = activity?.audit || {};
  const auditType = String(audit.type || '').toUpperCase();
  const isAuditedChange = ['ROUTE_CHANGE', 'DESTINATION_CHANGE', 'DRIVER_CHANGE'].includes(auditType)
    || /^Auditoria de rota:/i.test(String(activity?.message || ''));
  if (!isAuditedChange) return null;

  // New route audits include an immutable actor snapshot.  Some records that
  // were already saved before that change only have userName, so keep it as a
  // read-only fallback: the team can still identify who made the change in
  // the dashboard instead of seeing an anonymous audit line.
  const name = auditText(firstAuditValue(activity, 'actorName', 'userName') || firstAuditValue(audit, 'actorName', 'userName'), '');
  if (!name) return null;

  return {
    name,
    username: auditText(firstAuditValue(activity, 'actorUsername', 'username') || firstAuditValue(audit, 'actorUsername', 'username'), ''),
    role: auditText(firstAuditValue(activity, 'actorRole') || firstAuditValue(audit, 'actorRole'), '')
  };
}

function RecentActivityItem({ activity }) {
  const actor = recentAuditActor(activity);
  return <div className={classNames('activity', actor && 'activity-audited')}>
    <span className="activity-icon"><FileClock size={15} /></span>
    <div className="activity-copy">
      <p className="activity-message">{activity.message || 'Movimentação registrada.'}</p>
      {actor && <p className="activity-actor"><span>Alterado por:</span> <strong>{actor.name}</strong>{actor.username && <span> · @{actor.username}</span>}{actor.role && <span> · {roleLabel(actor.role)}</span>}</p>}
    </div>
    <time className="activity-time" dateTime={activity.at}>{time(activity.at)}</time>
  </div>;
}

function Dashboard({ data, user, token, refresh, notify, onAction, onCreate, onCreateTransfer, onTransferAction, setPage }) {
  const canManageTourQuantities = can(user, 'MANAGE_TOUR_QUANTITIES');
  const canManageTransfers = can(user, 'MANAGE_TRANSFERS');
  const canViewTransfers = canAccessPage(user, 'transfers');
  const tours = data.tours || [];
  const transfers = data.transfers || [];
  const settings = data.operationSettings || {};
  const count = (states) => tours.filter((tour) => states.includes(tour.status));
  const metrics = {
    available: count(['DISPONIVEL']), enTour: count(['EM_TOUR']), home: count(['NA_CASA', 'AGUARDANDO_CASA']), gallery: count(['AGUARDANDO_DESTINO']), destination: count(['EM_DESTINO_FINAL'])
  };
  const people = (items) => items.reduce((sum, tour) => sum + tour.people, 0);
  const activeTours = tours.filter((tour) => !['DISPONIVEL', 'CONCLUIDO', 'DESISTENCIA'].includes(tour.status)).slice(0, 5);
  const galleryTours = tours.filter((tour) => tour.status === 'AGUARDANDO_DESTINO');
  const houseTours = tours.filter((tour) => ['NA_CASA', 'AGUARDANDO_CASA'].includes(tour.status));
  const destTours = tours.filter((tour) => tour.status === 'AGUARDANDO_DESTINO');
  const consultantName = (tour) => tour.consultantName || data.consultants.find((item) => item.id === tour.consultantId)?.name || 'Sem consultor';
  return <>
    <OperationRestriction settings={settings} />
    {user.role === 'MOTORISTA' && can(user, 'MANAGE_HOSTESS_SUPPORT') && <DriverHostessAvailability data={data} user={user} token={token} refresh={refresh} notify={notify} />}
    <section className="page-title"><div><span>OPERAÇÃO EM TEMPO REAL</span><h1>Painel Geral</h1><p>Visão completa do fluxo de famílias, transporte e Galeria. Saída atual: {settings.departureLabel || 'Prestige Waves Bahia'}.</p></div>{canManageTourQuantities && <button className="button button-primary" onClick={onCreate}><Plus size={18} /> Quantidades de tours</button>}</section>
    <section className="metrics-grid">
      <MetricCard icon={Users} color="teal" title="Disponíveis no Prestige" count={metrics.available.length} sub={`${people(metrics.available)} pessoas`} />
      <MetricCard icon={CarFront} color="blue" title="Em tour" count={metrics.enTour.length} sub={`${people(metrics.enTour)} pessoas`} />
      <MetricCard icon={House} color="orange" title="Aguardando na Casa" count={metrics.home.length} sub={`${people(metrics.home)} pessoas`} />
      <MetricCard icon={Users} color="purple" title="Na Galeria" count={metrics.gallery.length} sub="aguardando destino" />
      <MetricCard icon={Check} color="green" title="Em destino final" count={metrics.destination.length} sub={`${people(metrics.destination)} pessoas`} />
      <MetricCard icon={Route} color="teal" title="Convites do Waves" count={transfers.filter((item) => item.status !== 'CHEGOU_PRESTIGE').length} sub={`${transfers.reduce((sum, item) => sum + item.people, 0)} convidados`} />
    </section>
    <Flow counts={metrics} />
    <section className="panel transfers-dashboard"><div className="panel-heading"><div><h2>Convites: Waves Bahia → Praia do Forte</h2><p>{settings.conciergePanelClosed ? 'Percurso Waves suspenso pelo fechamento de hotel.' : '07:50 para a 1ª Ola (09:00) · 09:50 para a 2ª Ola (11:00)'}</p></div>{(canManageTransfers || canViewTransfers) && <div className="heading-actions">{canManageTransfers && !settings.conciergePanelClosed && <button className="text-button" onClick={onCreateTransfer}>Novo convite</button>}{canViewTransfers && <button className="text-button" onClick={() => setPage('transfers')}>Ver todos</button>}</div>}</div><TransferTable transfers={transfers.slice(0, 3)} onAction={onTransferAction} user={user} settings={settings} /></section>
    <section className="dashboard-columns main-columns"><div className="panel"><div className="panel-heading"><div><h2>Tours em andamento</h2><p>Grupos em deslocamento e em etapas ativas</p></div>{canAccessPage(user, 'tours') && <button className="text-button" onClick={() => setPage('tours')}>Ver todos</button>}</div><TourTable tours={activeTours} data={data} user={user} onAction={onAction} compact /></div>
      <div className="panel gallery-panel"><div className="panel-heading"><div><h2>Na Galeria</h2><p>{galleryTours.length} grupos aguardando destino</p></div>{canAccessPage(user, 'gallery') && <button className="text-button" onClick={() => setPage('gallery')}>Ver todos</button>}</div><div className="gallery-list">{galleryTours.length ? galleryTours.map((tour) => { const name = consultantName(tour); return <div className="gallery-row" key={tour.id}><Avatar name={name} color="purple" /><div><strong>{tour.groupName}</strong><span>{name !== 'Sem consultor' && `Consultor: ${name} · `}{tour.people || '—'} pessoas · aguardando destino</span></div><StatusPill status={tour.status} /></div>; }) : <div className="empty-state">Galeria sem grupos no momento.</div>}</div></div></section>
    <section className="dashboard-columns bottom-columns"><div className="panel queue-panel"><div className="panel-heading"><div><h2>Aguardando na Casa</h2><p>Fila de transporte prioritária</p></div>{canAccessPage(user, 'home') && <button className="text-button" onClick={() => setPage('home')}>Ver todos</button>}</div><Queue items={houseTours} data={data} /></div>
      <div className="panel queue-panel"><div className="panel-heading"><div><h2>Aguardando destino final</h2><p>Chegaram à Galeria</p></div>{canAccessPage(user, 'destinations') && <button className="text-button" onClick={() => setPage('destinations')}>Ver todos</button>}</div><Queue items={destTours} data={data} destinations /></div>
      <div className="panel activity-panel"><div className="panel-heading"><div><h2>Atividade recente</h2><p>Rastreabilidade da operação</p></div></div><div className="activity-list">{(data.activities || []).slice(0, 4).map((activity) => <RecentActivityItem activity={activity} key={activity.id} />)}</div></div></section>
    <section className="panel drivers-panel"><div className="panel-heading"><div><h2>Status dos motoristas</h2><p>Disponibilidade, saídas e buscas na Casa</p></div>{canAccessPage(user, 'drivers') && <button className="text-button" onClick={() => setPage('drivers')}>Ver todos</button>}</div><div className="driver-grid">{data.drivers.map((driver) => <DriverCard key={driver.id} driver={driver} />)}</div></section>
  </>;
}

function HostessTourModal({ onClose, token, refresh, notify }) {
  const [quantity, setQuantity] = useState('0');
  const [selfGeanQuantity, setSelfGeanQuantity] = useState('0');
  const [wave, setWave] = useState('WAVE_1');
  const [saving, setSaving] = useState(false);
  async function submit(event) {
    event.preventDefault(); setSaving(true);
    try { await api(token, '/api/tours/hostess', { method: 'POST', body: JSON.stringify({ quantity: Number(quantity), selfGeanQuantity: Number(selfGeanQuantity), wave }) }); await refresh(); notify('Quantidades de tours registradas.', 'success'); onClose(); } catch (error) { notify(error.message, 'error'); } finally { setSaving(false); }
  }
  return <Modal title="Registrar quantidades de tours" onClose={onClose}><form className="modal-form" onSubmit={submit}><label>Quantidade de tours<input type="number" min="0" max="30" value={quantity} onChange={(event) => setQuantity(event.target.value)} required /></label><label>Quantidade de Self Gen<input type="number" min="0" max="30" value={selfGeanQuantity} onChange={(event) => setSelfGeanQuantity(event.target.value)} required /></label><label>Ola do tour<select value={wave} onChange={(event) => setWave(event.target.value)}>{Object.entries(WAVES).map(([key, item]) => <option value={key} key={key}>{item.label} · saída às {item.tourTime}</option>)}</select></label><div className="role-help">Tours e Self Gen são registrados separadamente, na Ola escolhida. Nome da família, hóspedes, consultor, carrinhos e motoristas não são informados nesta etapa.</div><button className="button button-primary" disabled={saving}>{saving && <LoaderCircle className="spin" size={17} />} Registrar quantidades</button></form></Modal>;
}

function HostessDashboard({ data, user, token, refresh, notify }) {
  const [open, setOpen] = useState(false);
  const [requestSaving, setRequestSaving] = useState(false);
  const tours = data.tours || [];
  const drivers = data.drivers || [];
  const requests = data.hostessRequests || [];
  const settings = data.operationSettings || {};
  const canCheckIn = can(user, 'CHECK_IN');
  const canRecordTourQuantities = can(user, 'MANAGE_TOUR_QUANTITIES');
  const canRequestCar = canAny(user, ['REQUEST_HOSTESS_CAR', 'MANAGE_HOSTESS_SUPPORT']);
  const activeTours = tours.filter((tour) => !['CONCLUIDO', 'DESISTENCIA'].includes(tour.status));
  const totalSelfGuide = activeTours.filter((tour) => tour.selfGuide);
  const normalTours = activeTours.filter((tour) => !tour.selfGuide);
  const enTour = tours.filter((tour) => tour.status === 'EM_TOUR');
  const awaitingDriver = tours.filter((tour) => tour.requiresDetails && tour.status === 'DISPONIVEL');
  const availableDrivers = drivers.filter((driver) => driver.status === 'DISPONIVEL' && !driver.hostessAvailable).length;
  const ownRequest = requests.find((item) => item.status === 'SOLICITADO' && item.requestedById === user.id);
  const openRequests = requests.filter((item) => item.status === 'SOLICITADO');
  const hostessDrivers = drivers.filter((driver) => driver.hostessAvailable && driver.status === 'APOIO_HOSTESS');
  const assignedDriverName = ownRequest?.assignedDriverName;
  async function requestCar() {
    setRequestSaving(true);
    try { await api(token, '/api/hostess-requests', { method: 'POST' }); await refresh(); notify('Solicitação de carro enviada aos motoristas.', 'success'); } catch (error) { notify(error.message, 'error'); } finally { setRequestSaving(false); }
  }
  async function closeRequest() {
    setRequestSaving(true);
    try { await api(token, `/api/hostess-requests/${ownRequest.id}/close`, { method: 'POST' }); await refresh(); notify('Solicitação de carro encerrada.', 'success'); } catch (error) { notify(error.message, 'error'); } finally { setRequestSaving(false); }
  }
  return <>
    {canCheckIn && <CheckInCard data={data} user={user} token={token} refresh={refresh} notify={notify} />}
    <OperationRestriction settings={settings} />
    <section className="page-title hostess-title"><div><span>PAINEL GERAL · HOSTESS</span><h1>Painel Geral</h1><p>Visualização da operação. As opções disponíveis seguem as permissões do seu usuário.</p></div>{canRecordTourQuantities && <button className="button button-primary" onClick={() => setOpen(true)}><Plus size={18} /> Quantidades de tours</button>}</section>
    {canRequestCar && <><section className="hostess-call"><div><span>SOLICITAÇÃO DE CARRO</span><h2>{ownRequest ? assignedDriverName ? `${assignedDriverName} está em apoio` : 'Carro solicitado' : 'Precisa de um carro?'}</h2><p>{ownRequest ? assignedDriverName ? 'O motorista encerra este chamado ao finalizar o apoio. Se necessário, você também pode encerrá-lo agora.' : 'Aguarde um motorista assumir este chamado. Não é necessário informar hotel, destino ou motorista.' : openRequests.length ? 'Há outro pedido em aberto. Você pode fazer o seu próprio pedido de carro.' : 'Toque no botão para avisar os motoristas livres. Não é necessário informar hotel, destino ou motorista.'}</p></div>{ownRequest ? <button className="button button-secondary" onClick={closeRequest} disabled={requestSaving}>{requestSaving && <LoaderCircle className="spin" size={17} />} Encerrar solicitação</button> : <button className="button button-primary" onClick={requestCar} disabled={requestSaving}>{requestSaving && <LoaderCircle className="spin" size={18} />} <CarFront size={18} /> Solicitar carro</button>}</section>
    <section className="available-hostess-drivers"><div><h2>Motoristas em apoio à Hostess</h2><p>{openRequests.length ? 'Os motoristas desta lista estão reservados exclusivamente para este apoio.' : 'Abra uma solicitação para os motoristas responderem.'}</p></div><div>{hostessDrivers.length ? hostessDrivers.map((driver) => <span className="hostess-driver" key={driver.id}><Check size={15} /> {driver.name}</span>) : <span className="hostess-empty">Nenhum motorista assumiu o apoio ainda.</span>}</div></section></>}
    <section className="metrics-grid hostess-general-metrics"><MetricCard icon={Route} color="teal" title="Tours normais" count={normalTours.length} sub={`${awaitingDriver.length} aguardando motorista`} /><MetricCard icon={Flag} color="purple" title="Self Gen" count={totalSelfGuide.length} sub="registros do dia" /><MetricCard icon={CarFront} color="blue" title="Em tour" count={enTour.length} sub="grupos em deslocamento" /><MetricCard icon={Check} color="green" title="Motoristas disponíveis" count={availableDrivers} sub={`${drivers.length} motoristas ativos`} /></section>
    <section className="panel drivers-panel"><div className="panel-heading"><div><h2>Status dos motoristas</h2><p>Somente visualização para a Hostess.</p></div></div><div className="driver-grid">{drivers.map((driver) => <DriverCard key={driver.id} driver={driver} />)}</div></section>
    <section className="panel hostess-note"><h2>Acesso ao Painel Geral</h2><p>{canRecordTourQuantities || canRequestCar ? 'Você só vê as funções liberadas pelo administrador para sua conta.' : 'Seu acesso é somente de visualização: não há botão para alterar tours, motoristas ou solicitações.'}</p></section>
    {open && canRecordTourQuantities && <HostessTourModal onClose={() => setOpen(false)} token={token} refresh={refresh} notify={notify} />}
  </>;
}

function HostessPrestigePage({ data, user, token, refresh, notify }) {
  const [open, setOpen] = useState(false);
  const departureLabel = data.operationSettings?.departureLabel || 'Prestige Waves Bahia';
  const awaitingDriver = (data.tours || []).filter((tour) => tour.requiresDetails && tour.status === 'DISPONIVEL');
  const activeTours = (data.tours || []).filter((tour) => !['CONCLUIDO', 'DESISTENCIA'].includes(tour.status));
  const normalToursToday = activeTours.filter((tour) => !tour.selfGuide).length;
  const selfGeanToday = activeTours.filter((tour) => tour.selfGuide).length;
  return <><CheckInCard data={data} user={user} token={token} refresh={refresh} notify={notify} /><section className="page-title"><div><span>CONTROLE OPERACIONAL</span><h1>{departureLabel}</h1><p>A Hostess registra separadamente as quantidades de tours, Self Gen e a Ola.</p></div><button className="button button-primary" onClick={() => setOpen(true)}><Plus size={18} /> Quantidades de tours</button></section><section className="hostess-grid"><article><Route size={35} /><div><span>TOURS NORMAIS</span><strong>{normalToursToday}</strong><small>{awaitingDriver.length} aguardando motorista</small></div></article><article><Flag size={35} /><div><span>SELF GEN</span><strong>{selfGeanToday}</strong><small>registros Self Gen na operação</small></div></article></section><section className="panel hostess-note"><h2>Registro simplificado</h2><p>Nesta aba a Hostess não informa família, consultor, quantidade de hóspedes ou motoristas: somente as quantidades de tours e Self Gen, mais a Ola.</p></section>{open && <HostessTourModal onClose={() => setOpen(false)} token={token} refresh={refresh} notify={notify} />}</>;
}

function Queue({ items, data, destinations = false }) {
  if (!items.length) return <div className="empty-state">Nenhum grupo aguardando.</div>;
  return <div className="queue-list">{items.map((tour) => {
    const consultantName = tour.consultantName || (data.consultants || []).find((item) => item.id === tour.consultantId)?.name;
    const destination = destinations ? (data.destinations || []).find((item) => item.id === tour.destinationId)?.name || 'Destino pendente' : 'Aguardando transporte';
    return <div className="queue-row" key={tour.id}><Avatar name={consultantName || tour.groupName} color="orange" /><div><strong>{tour.groupName}</strong><span>{consultantName && `Consultor: ${consultantName} · `}{tour.people} pessoas · {destination}</span></div><ChevronRight size={18} /></div>;
  })}</div>;
}

function SectionHeader({ title, description, action, actionText = 'Novo tour' }) {
  return <section className="page-title"><div><span>CONTROLE OPERACIONAL</span><h1>{title}</h1><p>{description}</p></div>{action && <button className="button button-primary" onClick={action}><Plus size={18} /> {actionText}</button>}</section>;
}

function OperationalPage({ page, data, user, onAction, onCreate }) {
  const settings = data.operationSettings || {};
  const options = {
    prestige: { title: settings.departureLabel || 'Prestige Waves Bahia', description: settings.toursClosed ? 'Novas saídas de tour estão suspensas porque os dois hotéis estão fechados.' : 'Grupos disponíveis para iniciar o tour.', tours: data.tours.filter((tour) => tour.status === 'DISPONIVEL') },
    tours: { title: 'Tours em andamento', description: 'Acompanhe e avance os grupos por cada etapa operacional.', tours: data.tours.filter((tour) => !['DISPONIVEL', 'CONCLUIDO', 'DESISTENCIA'].includes(tour.status)) },
    home: { title: 'Casa', description: 'Grupos na Casa e fila aguardando transporte.', tours: data.tours.filter((tour) => ['NA_CASA', 'AGUARDANDO_CASA'].includes(tour.status)) },
    destinations: { title: 'Destinos finais', description: 'Grupos que chegaram à Galeria e aguardam ou seguem para o destino final.', tours: data.tours.filter((tour) => ['AGUARDANDO_DESTINO', 'EM_DESTINO_FINAL'].includes(tour.status)) }
  }[page];
  return <><OperationRestriction settings={settings} /><SectionHeader {...options} action={can(user, 'MANAGE_TOUR_QUANTITIES') && page === 'prestige' ? onCreate : undefined} actionText="Quantidade de tours" /><section className="panel full-panel"><TourTable tours={options.tours} data={data} user={user} onAction={onAction} /></section></>;
}

function TransfersPage({ data, user, onCreate, onAction }) {
  const settings = data.operationSettings || {};
  const allTransfers = data.transfers || [];
  const transfers = user.role === 'CONCIERGE' ? allTransfers.filter((transfer) => transfer.conciergeUserId === user.id) : allTransfers;
  const activeTransfers = transfers.filter((transfer) => transfer.status !== 'DESISTENCIA');
  const withdrawals = transfers.filter((transfer) => transfer.status === 'DESISTENCIA');
  const byWave = (wave) => activeTransfers.filter((transfer) => transfer.wave === wave && transfer.status !== 'CHEGOU_PRESTIGE');
  const description = settings.conciergePanelClosed ? 'O percurso Waves está suspenso enquanto houver hotel fechado no período.' : user.role === 'CONCIERGE' ? 'Cadastre somente as suas famílias/casais convidados e a quantidade de pessoas.' : 'Traslado dos hóspedes convidados pelos concierges para acompanhar os consultores no tour.';
  return <><OperationRestriction settings={settings} /><SectionHeader title="Convites Waves → Praia do Forte" description={description} action={settings.conciergePanelClosed || !can(user, 'MANAGE_TRANSFERS') ? undefined : onCreate} actionText="Novo convite" /><section className="transfer-metrics"><MetricCard icon={Users} color="teal" title="Famílias convidadas" count={activeTransfers.length} sub={`${activeTransfers.reduce((sum, item) => sum + item.people, 0)} pessoas convidadas`} /><MetricCard icon={Flag} color="orange" title="Desistências" count={withdrawals.length} sub="convites não confirmados" /></section><section className="wave-schedule-grid">{Object.entries(WAVES).map(([wave, schedule]) => <article key={wave}><Route size={26} /><div><span>{schedule.label.toUpperCase()}</span><strong>{schedule.transferTime}</strong><p>Waves Bahia <ChevronRight size={13} /> Praia do Forte</p><small>Conecta ao tour das {schedule.tourTime} · {byWave(wave).length} convite{byWave(wave).length === 1 ? '' : 's'} pendente{byWave(wave).length === 1 ? '' : 's'}</small></div></article>)}</section><section className="panel full-panel"><div className="panel-heading"><div><h2>{user.role === 'CONCIERGE' ? 'Meus convites de hoje' : 'Convites de hoje'}</h2><p>{user.role === 'CONCIERGE' ? 'Você pode registrar a desistência de um casal ou família antes do traslado.' : 'O traslado não possui horário de encerramento; a chegada é registrada quando acontecer.'}</p></div></div><TransferTable transfers={transfers} onAction={onAction} user={user} settings={settings} empty="Nenhum convite cadastrado." /></section></>;
}

function ConciergeClosedPage({ data }) {
  const closedHotels = (data.operationSettings?.activeClosures || []).map((item) => item.hotelLabel).join(', ');
  return <section className="restricted"><Route size={35} /><h1>Sem percurso Waves no período</h1><p>{closedHotels ? `${closedHotels} está fechado. O painel do Concierge volta automaticamente quando o período terminar.` : 'O painel do Concierge está indisponível enquanto não houver percurso Waves.'}</p></section>;
}

function GalleryPage({ data, user, onAction }) {
  const tours = data.tours.filter((tour) => tour.status === 'AGUARDANDO_DESTINO');
  return <><SectionHeader title="Galeria" description="Ao chegar à Galeria, o grupo aguarda diretamente o destino final. Não há etapa de apresentação." /><section className="gallery-summary"><article><Image /><div><small>GRUPOS NA GALERIA</small><strong>{tours.length}</strong></div></article><article><Users /><div><small>AGUARDANDO DESTINO</small><strong>{tours.length}</strong></div></article></section><section className="panel full-panel"><TourTable tours={tours} data={data} user={user} onAction={onAction} empty="Nenhum grupo aguardando destino na Galeria." /></section></>;
}

function DriverEditorModal({ driver, onClose, token, refresh, notify }) {
  const editing = Boolean(driver);
  const [form, setForm] = useState({ name: driver?.name || '', active: driver?.active ?? true, status: driver?.status || 'DISPONIVEL' });
  const [saving, setSaving] = useState(false);
  async function submit(event) {
    event.preventDefault(); setSaving(true);
    try { await api(token, editing ? `/api/drivers/${driver.id}` : '/api/drivers', { method: editing ? 'PUT' : 'POST', body: JSON.stringify(form) }); await refresh(); notify(editing ? 'Motorista atualizado.' : 'Motorista cadastrado.', 'success'); onClose(); } catch (error) { notify(error.message, 'error'); } finally { setSaving(false); }
  }
  return <Modal title={editing ? 'Editar motorista' : 'Novo motorista'} onClose={onClose}><form className="modal-form" onSubmit={submit}><label>Nome<input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} required /></label><label>Disponibilidade<select value={form.status} onChange={(event) => setForm({ ...form, status: event.target.value })}>{Object.entries(DRIVER_STATUS).map(([value, meta]) => <option key={value} value={value}>{meta.label}</option>)}</select></label><label className="checkbox-label"><input type="checkbox" checked={form.active} onChange={(event) => setForm({ ...form, active: event.target.checked })} /> Cadastro ativo</label><button className="button button-primary" disabled={saving}>{saving && <LoaderCircle className="spin" size={17} />} {editing ? 'Salvar alterações' : 'Cadastrar motorista'}</button></form></Modal>;
}

function DriversPage({ data, user, token, refresh, notify }) {
  const [editing, setEditing] = useState(null);
  const [deleting, setDeleting] = useState(null);
  const [savingDelete, setSavingDelete] = useState(false);
  const canManageDrivers = can(user, 'MANAGE_DRIVERS');
  async function removeDriver() {
    setSavingDelete(true);
    try { await api(token, `/api/drivers/${deleting.id}`, { method: 'DELETE' }); await refresh(); setDeleting(null); notify('Motorista excluído.', 'success'); } catch (error) { notify(error.message, 'error'); } finally { setSavingDelete(false); }
  }
  return <><SectionHeader title="Motoristas" description="Disponibilidade, tours iniciados no Prestige e buscas realizadas na Casa." action={canManageDrivers ? () => setEditing({}) : undefined} actionText="Novo motorista" /><section className="driver-page-grid">{data.drivers.map((driver) => <DriverCard key={driver.id} driver={driver} />)}</section><section className="panel full-panel"><div className="panel-heading"><div><h2>Indicadores por motorista</h2><p>{canManageDrivers ? 'Você pode alterar situação, atividade e cadastro.' : 'Somente visualização dos indicadores de motoristas.'}</p></div></div><div className="table-wrap"><table><thead><tr><th>Motorista</th><th>Status</th><th>Cadastro</th><th>Tours iniciados</th><th>Buscas na Casa</th><th>Última atividade</th>{canManageDrivers && <th>Ações</th>}</tr></thead><tbody>{data.drivers.map((driver) => <tr key={driver.id}><td><div className="name-cell"><Avatar name={driver.name} color="photo" /><strong>{driver.name}</strong></div></td><td><StatusPill driver status={driver.status} /></td><td><span className={driver.active ? 'active-dot' : 'inactive-dot'}>{driver.active ? 'Ativo' : 'Inativo'}</span></td><td>{driver.toursStarted}</td><td>{driver.homePickups}</td><td>{time(driver.lastActivity)}</td>{canManageDrivers && <td className="actions-cell"><button className="mini-action" onClick={() => setEditing(driver)} disabled={driver.hostessAvailable} title={driver.hostessAvailable ? 'Encerre o apoio da Hostess antes de editar este motorista.' : undefined}>Editar</button><button className="mini-action danger-mini" onClick={() => setDeleting(driver)} disabled={driver.hostessAvailable} title={driver.hostessAvailable ? 'Encerre o apoio da Hostess antes de excluir este motorista.' : undefined}>Excluir</button></td>}</tr>)}</tbody></table></div></section>{editing && <DriverEditorModal key={editing.id || 'new'} driver={editing.id ? editing : null} onClose={() => setEditing(null)} token={token} refresh={refresh} notify={notify} />}{deleting && <Modal title="Excluir motorista" onClose={() => setDeleting(null)}><div className="danger-copy"><CarFront size={25} /><p>Excluir <strong>{deleting.name}</strong> removerá o cadastro. Motoristas vinculados a um tour ativo precisam ser liberados antes.</p></div><div className="modal-actions"><button className="button button-secondary" onClick={() => setDeleting(null)}>Cancelar</button><button className="button button-danger" onClick={removeDriver} disabled={savingDelete}>{savingDelete && <LoaderCircle className="spin" size={17} />} Excluir</button></div></Modal>}</>;
}

function ConsultantEditorModal({ consultant, onClose, token, refresh, notify }) {
  const editing = Boolean(consultant);
  const [form, setForm] = useState({ name: consultant?.name || '', active: consultant?.active ?? true });
  const [saving, setSaving] = useState(false);
  async function submit(event) {
    event.preventDefault(); setSaving(true);
    try { await api(token, editing ? `/api/consultants/${consultant.id}` : '/api/consultants', { method: editing ? 'PUT' : 'POST', body: JSON.stringify(form) }); await refresh(); notify(editing ? 'Consultor atualizado.' : 'Consultor cadastrado.', 'success'); onClose(); } catch (error) { notify(error.message, 'error'); } finally { setSaving(false); }
  }
  return <Modal title={editing ? 'Editar consultor' : 'Novo consultor'} onClose={onClose}><form className="modal-form" onSubmit={submit}><label>Nome<input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} required /></label><label className="checkbox-label"><input type="checkbox" checked={form.active} onChange={(event) => setForm({ ...form, active: event.target.checked })} /> Cadastro ativo</label><button className="button button-primary" disabled={saving}>{saving && <LoaderCircle className="spin" size={17} />} {editing ? 'Salvar alterações' : 'Cadastrar consultor'}</button></form></Modal>;
}

function ConsultantsPage({ data, user, token, refresh, notify }) {
  const [editing, setEditing] = useState(null);
  const [deleting, setDeleting] = useState(null);
  const [savingDelete, setSavingDelete] = useState(false);
  const canManageConsultants = can(user, 'MANAGE_CONSULTANTS');
  const currentTours = data.tours.filter((tour) => !['CONCLUIDO', 'DESISTENCIA'].includes(tour.status));
  async function removeConsultant() {
    setSavingDelete(true);
    try { await api(token, `/api/consultants/${deleting.id}`, { method: 'DELETE' }); await refresh(); setDeleting(null); notify('Consultor excluído.', 'success'); } catch (error) { notify(error.message, 'error'); } finally { setSavingDelete(false); }
  }
  return <><SectionHeader title="Consultores" description="Consultores vinculados aos grupos da operação." action={canManageConsultants ? () => setEditing({}) : undefined} actionText="Novo consultor" /><section className="consultants-grid">{data.consultants.map((consultant) => { const tours = currentTours.filter((tour) => tour.consultantId === consultant.id); return <article className="consultant-card" key={consultant.id}><Avatar name={consultant.name} color="pink" /><h2>{consultant.name}</h2><span className={consultant.active ? 'active-dot' : 'inactive-dot'}>{consultant.active ? 'Ativo' : 'Inativo'}</span><div><strong>{tours.length}</strong><small>grupos ativos</small></div>{canManageConsultants && <p className="card-actions"><button className="mini-action" onClick={() => setEditing(consultant)}>Editar</button><button className="mini-action danger-mini" onClick={() => setDeleting(consultant)}>Excluir</button></p>}</article>; })}</section>{editing && <ConsultantEditorModal key={editing.id || 'new'} consultant={editing.id ? editing : null} onClose={() => setEditing(null)} token={token} refresh={refresh} notify={notify} />}{deleting && <Modal title="Excluir consultor" onClose={() => setDeleting(null)}><div className="danger-copy"><UserRound size={25} /><p>Excluir <strong>{deleting.name}</strong> remove o cadastro, preservando apenas os registros antigos de tours.</p></div><div className="modal-actions"><button className="button button-secondary" onClick={() => setDeleting(null)}>Cancelar</button><button className="button button-danger" onClick={removeConsultant} disabled={savingDelete}>{savingDelete && <LoaderCircle className="spin" size={17} />} Excluir</button></div></Modal>}</>;
}

function CartsPage({ data }) {
  return <><SectionHeader title="Carrinhos" description="Cada carrinho leva 5 passageiros além do motorista: 1 consultor e até 4 hóspedes." /><section className="carts-grid">{data.carts.map((cart) => <article className="cart-card" key={cart.id}><div className={cart.status === 'DISPONIVEL' ? 'cart-icon available' : 'cart-icon'}><ShoppingCart size={27} /></div><h2>{cart.name}</h2><p><strong>{cart.capacity} lugares</strong> para passageiros</p><small className="cart-capacity-note">1 consultor + até {cart.guestCapacity || 4} hóspedes</small><span className={classNames('status-pill', cart.status === 'DISPONIVEL' ? 'tone-green' : 'tone-blue')}>{cart.status === 'DISPONIVEL' ? 'Disponível' : 'Em uso'}</span></article>)}</section></>;
}

function HistoryPage({ data }) {
  const activities = data.activities || [];
  return <><SectionHeader title="Histórico e auditoria" description="Todas as movimentações relevantes da operação são registradas aqui." /><section className="panel full-panel"><div className="history-list">{activities.length === 0 ? <div className="empty-state">Nenhuma movimentação registrada nesta operação.</div> : activities.map((activity) => {
    const audit = activity.audit || {};
    const auditType = String(audit.type || '').toUpperCase();
    const routeChange = auditType === 'ROUTE_CHANGE';
    const driverChange = auditType === 'DRIVER_CHANGE';
    const audited = routeChange || driverChange;
    const actorName = firstAuditValue(activity, 'actorName', 'userName') || firstAuditValue(audit, 'actorName', 'userName') || 'Sistema';
    const actorUsername = firstAuditValue(activity, 'actorUsername', 'username') || firstAuditValue(audit, 'actorUsername', 'username');
    const actorRole = firstAuditValue(activity, 'actorRole') || firstAuditValue(audit, 'actorRole');
    const tourName = auditText(firstAuditValue(audit, 'tourName', 'groupName') || firstAuditValue(activity, 'tourName', 'groupName'), 'Tour não informado');
    const consultantName = auditText(firstAuditValue(audit, 'consultantName') || firstAuditValue(activity, 'consultantName'), 'Sem consultor informado');
    const affectedDrivers = auditText(firstAuditValue(audit, 'driverNames', 'affectedDrivers', 'drivers'), 'Nenhum motorista informado');
    const previousRoute = auditText(firstAuditValue(audit, 'from', 'previousRoute', 'before', 'previous', 'previousStatus'), 'Não informado');
    const nextRoute = auditText(firstAuditValue(audit, 'to', 'nextRoute', 'after', 'next', 'nextStatus'), 'Não informado');
    const driverName = auditText(firstAuditValue(audit, 'driverName', 'affectedDriverName'), 'Motorista não informado');
    const previousDriverName = auditText(firstAuditValue(audit, 'previousName'), '');
    const driverLabel = previousDriverName && previousDriverName !== driverName ? `${previousDriverName} → ${driverName}` : driverName;
    const title = routeChange ? 'Alteração de rota registrada' : driverChange ? 'Alteração de motorista registrada' : (activity.message || 'Movimentação registrada');
    return <article className={classNames('history-entry', routeChange && 'history-entry-route-audit', driverChange && 'history-entry-driver-audit')} key={activity.id}><span className="history-mark"><FileClock size={18} /></span><div className="history-copy">{audited && <span className={classNames('history-audit-type', routeChange ? 'history-audit-route-type' : 'history-audit-driver-type')}>{routeChange ? 'ALTERAÇÃO DE ROTA' : 'ALTERAÇÃO MANUAL DE MOTORISTA'}</span>}<h3>{title}</h3>{audited && activity.message && <p className="history-message">{activity.message}</p>}{routeChange && <div className="history-audit-details"><dl className="history-audit-grid"><div><dt>Quem alterou</dt><dd>{actorName}<small>{actorUsername ? `Conta: @${actorUsername}` : 'Conta não informada'}{actorRole && ` · ${roleLabel(actorRole)}`}</small></dd></div><div><dt>Tour</dt><dd>{tourName}<small>Consultor: {consultantName}</small></dd></div><div className="history-audit-wide"><dt>Rota alterada</dt><dd className="history-audit-route"><span>{previousRoute}</span><ChevronRight size={15} /><span>{nextRoute}</span></dd></div><div className="history-audit-wide"><dt>Motoristas afetados</dt><dd>{affectedDrivers}</dd></div></dl></div>}{driverChange && <div className="history-audit-details"><dl className="history-audit-grid"><div><dt>Quem alterou</dt><dd>{actorName}<small>{actorUsername ? `Conta: @${actorUsername}` : 'Conta não informada'}{actorRole && ` · ${roleLabel(actorRole)}`}</small></dd></div><div><dt>Motorista alterado</dt><dd>{driverLabel}</dd></div><div className="history-audit-wide"><dt>Alteração</dt><dd className="history-audit-route"><span>{previousRoute}</span><ChevronRight size={15} /><span>{nextRoute}</span></dd></div></dl></div>}<p className="history-meta">{audited ? `Registrado em ${activityDateLabel(activity.at)}` : `${activity.userName || 'Sistema'} · ${activityDateLabel(activity.at)}`}</p>{!audited && activity.previous && <div className="history-state"><StatusPill status={activity.previous} /><ChevronRight size={14} /><StatusPill status={activity.next} /></div>}</div></article>;
  })}</div></section></>;
}

function ReportsPage({ data }) {
  const active = data.tours.filter((tour) => !['CONCLUIDO', 'DESISTENCIA'].includes(tour.status));
  const selfGean = active.filter((tour) => tour.selfGuide);
  const availableDrivers = data.drivers.filter((driver) => driver.status === 'DISPONIVEL' && !driver.hostessAvailable);
  const departureLabel = data.operationSettings?.departureLabel || 'Prestige Waves Bahia';
  return <><SectionHeader title="Relatórios" description="Indicadores rápidos para a coordenação da operação." /><section className="report-grid"><MetricCard icon={Route} color="blue" title="Tours ativos" count={active.length} sub={`${active.reduce((sum, tour) => sum + tour.people, 0)} pessoas`} /><MetricCard icon={Flag} color="orange" title="Grupos Self Gen" count={selfGean.length} sub={`${selfGean.reduce((sum, tour) => sum + tour.people, 0)} pessoas`} /><MetricCard icon={CarFront} color="green" title="Motoristas disponíveis" count={availableDrivers.length} sub={`${data.drivers.length} cadastrados`} /><MetricCard icon={ShoppingCart} color="purple" title="Carrinhos em operação" count={data.carts.filter((cart) => cart.status !== 'DISPONIVEL').length} sub={`${data.carts.length} cadastrados`} /></section><section className="panel full-panel"><div className="panel-heading"><div><h2>Saídas por motorista</h2><p>Contagem de tours iniciados no {departureLabel}.</p></div></div><div className="bar-list">{data.drivers.map((driver) => <div key={driver.id}><span>{driver.name}</span><div><i style={{ width: `${Math.max(8, Math.round((driver.toursStarted / Math.max(...data.drivers.map((item) => item.toursStarted), 1)) * 100))}%` }} /></div><strong>{driver.toursStarted}</strong></div>)}</div></section></>;
}

function selectedPermissionsForAccount(account, catalog) {
  return accountPermissions(account) ?? defaultPermissionsForRole(account?.role || 'MOTORISTA', catalog);
}

function PermissionSummary({ permissions, catalog, fallbackRole }) {
  const codes = Array.from(new Set((permissions ?? defaultPermissionsForRole(fallbackRole, catalog)).map(normalizedPermissionCode)));
  const labels = codes.map((code) => catalog.find((item) => normalizedPermissionCode(item.code) === code)?.label || code.replace(/_/g, ' '));
  if (codes.length === 1 && codes[0] === 'VIEW_DASHBOARD') return <span className="permission-summary permission-summary-readonly">Painel Geral · somente visualização</span>;
  if (!labels.length) return <span className="permission-summary permission-summary-none">Sem permissões</span>;
  const visible = labels.slice(0, 2);
  const remaining = labels.length - visible.length;
  return <span className="permission-summary" title={labels.join(' · ')}>{visible.join(' · ')}{remaining > 0 && <small>+{remaining}</small>}</span>;
}

function UserEditorModal({ account, drivers, permissionCatalog: catalogInput, onClose, token, refresh, notify }) {
  const editing = Boolean(account);
  const catalog = permissionCatalog(catalogInput);
  const initialPermissions = selectedPermissionsForAccount(account, catalog);
  const [form, setForm] = useState({ name: account?.name || '', username: account?.username || '', password: '', role: account?.role || 'MOTORISTA', active: account?.active ?? true, driverId: account?.driverId || '', checkInLocation: account?.checkInLocation || 'Prestige Praia do Forte', permissions: initialPermissions });
  const [saving, setSaving] = useState(false);
  const [permissionsRole, setPermissionsRole] = useState(account?.role || 'MOTORISTA');
  const permissionGroups = catalog.reduce((groups, permission) => {
    const group = permission.group || 'Outras permissões';
    groups[group] = [...(groups[group] || []), permission];
    return groups;
  }, {});
  const selectedPermissions = new Set(form.permissions.map(normalizedPermissionCode));
  const readOnlyDashboard = selectedPermissions.size === 1 && selectedPermissions.has('VIEW_DASHBOARD');
  useEffect(() => {
    if (form.role === permissionsRole) return;
    setForm((current) => ({ ...current, permissions: defaultPermissionsForRole(current.role, catalog) }));
    setPermissionsRole(form.role);
  }, [form.role, permissionsRole, catalog]);
  function togglePermission(code) {
    const normalized = normalizedPermissionCode(code);
    setForm((current) => ({ ...current, permissions: current.permissions.map(normalizedPermissionCode).includes(normalized) ? current.permissions.filter((item) => normalizedPermissionCode(item) !== normalized) : [...current.permissions, normalized] }));
  }
  function applyRoleDefaults() {
    setForm((current) => ({ ...current, permissions: defaultPermissionsForRole(current.role, catalog) }));
  }
  async function submit(event) {
    event.preventDefault(); setSaving(true);
    const payload = { ...form, permissions: Array.from(new Set(form.permissions.map(normalizedPermissionCode))) };
    try { await api(token, editing ? `/api/users/${account.id}` : '/api/users', { method: editing ? 'PUT' : 'POST', body: JSON.stringify(payload) }); await refresh(); notify(editing ? 'Usuário atualizado.' : 'Usuário criado com sucesso.', 'success'); onClose(); } catch (error) { notify(error.message, 'error'); } finally { setSaving(false); }
  }
  return <Modal title={editing ? 'Editar usuário' : 'Criar usuário'} onClose={onClose}><form className="modal-form" onSubmit={submit}><label>Nome<input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} required /></label><label>Usuário<input value={form.username} onChange={(event) => setForm({ ...form, username: event.target.value })} required /></label><label>{editing ? 'Nova senha (opcional)' : 'Senha inicial'}<input type="password" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} minLength="8" required={!editing} /></label><label>Perfil<select value={form.role} onChange={(event) => { const role = event.target.value; setForm({ ...form, role, driverId: role === 'MOTORISTA' ? form.driverId : '' }); }}><option value="MOTORISTA">Motorista</option><option value="HOSTESS">Hostess</option><option value="CONCIERGE">Concierge</option><option value="VISUALIZADOR">Somente visualização</option><option value="ADMIN">Administrador</option></select></label>{form.role === 'MOTORISTA' && <label>Motorista vinculado<select value={form.driverId} onChange={(event) => setForm({ ...form, driverId: event.target.value })}><option value="">Criar automaticamente com este nome</option>{drivers.map((driver) => <option key={driver.id} value={driver.id}>{driver.name}</option>)}</select></label>}{['MOTORISTA', 'HOSTESS'].includes(form.role) && <label>Local de check-in<input value={form.checkInLocation} onChange={(event) => setForm({ ...form, checkInLocation: event.target.value })} placeholder="Ex.: Prestige Praia do Forte" required /></label>}<fieldset className="permissions-fieldset"><div className="permissions-heading"><div><legend>Permissões de acesso</legend><p>Marque exatamente o que este usuário pode ver ou fazer.</p></div><button type="button" className="text-button" onClick={applyRoleDefaults}>Usar sugestão do perfil</button></div><div className="permissions-readonly-note"><ShieldCheck size={17} /><span><strong>Ver Painel Geral</strong> sozinho deixa a conta em modo somente visualização: sem botões para alterar tours, motoristas ou cadastros.</span></div><div className="permission-groups">{Object.entries(permissionGroups).map(([group, permissions]) => <section className="permission-group" key={group}><h3>{group}</h3>{permissions.map((permission) => <label className="permission-option" key={permission.code}><input type="checkbox" checked={selectedPermissions.has(normalizedPermissionCode(permission.code))} onChange={() => togglePermission(permission.code)} /><span><strong>{permission.label}</strong><small>{permission.description}</small></span></label>)}</section>)}</div><div className="permission-selection-summary"><span>{selectedPermissions.size} permissão{selectedPermissions.size === 1 ? '' : 'ões'} selecionada{selectedPermissions.size === 1 ? '' : 's'}</span><PermissionSummary permissions={form.permissions} catalog={catalog} fallbackRole={form.role} />{readOnlyDashboard && <strong>Esta conta só poderá visualizar o Painel Geral.</strong>}</div></fieldset><label className="checkbox-label"><input type="checkbox" checked={form.active} onChange={(event) => setForm({ ...form, active: event.target.checked })} /> Usuário ativo</label><div className="role-help"><strong>Motorista:</strong> sem vínculo selecionado, o cadastro operacional é criado automaticamente e fica disponível após o check-in. <strong>Concierge:</strong> registra somente seus convites Waves e desistências; não cria nem mantém cadastro de motorista.</div><button className="button button-primary" disabled={saving}>{saving && <LoaderCircle className="spin" size={17} />} {editing ? 'Salvar alterações' : 'Criar usuário'}</button></form></Modal>;
}

function OperationSettingsPanel({ data, token, refresh, notify }) {
  const settings = data.operationSettings || {};
  const [defaultDeparture, setDefaultDeparture] = useState(data.defaultDeparturePrestige || 'BAHIA');
  const [closure, setClosure] = useState({ hotel: 'WAVES_BAHIA', startDate: data.operationDate || '', endDate: data.operationDate || '', departurePrestige: 'SELECTION' });
  const [saving, setSaving] = useState(false);
  const closures = [...(data.hotelClosures || [])].sort((left, right) => right.startDate.localeCompare(left.startDate));
  function changeHotel(hotel) { setClosure((current) => ({ ...current, hotel, departurePrestige: hotel === 'WAVES_BAHIA' ? 'SELECTION' : 'BAHIA' })); }
  async function saveDefault() {
    setSaving(true);
    try { await api(token, '/api/operation/departure-prestige', { method: 'POST', body: JSON.stringify({ departurePrestige: defaultDeparture }) }); await refresh(); notify('Prestige de saída padrão atualizado.', 'success'); } catch (error) { notify(error.message, 'error'); } finally { setSaving(false); }
  }
  async function addClosure(event) {
    event.preventDefault(); setSaving(true);
    try { await api(token, '/api/hotel-closures', { method: 'POST', body: JSON.stringify(closure) }); await refresh(); notify('Período de fechamento configurado.', 'success'); setClosure((current) => ({ ...current, startDate: data.operationDate || '', endDate: data.operationDate || '' })); } catch (error) { notify(error.message, 'error'); } finally { setSaving(false); }
  }
  async function removeClosure(item) {
    setSaving(true);
    try { await api(token, `/api/hotel-closures/${item.id}`, { method: 'DELETE' }); await refresh(); notify('Fechamento removido.', 'success'); } catch (error) { notify(error.message, 'error'); } finally { setSaving(false); }
  }
  return <section className="operation-settings"><div className="panel-heading"><div><h2>Hotéis e Prestige de saída</h2><p>Escolha o ponto padrão de saída e cadastre períodos de fechamento. A mudança vale automaticamente nas datas informadas, sem novo deploy.</p></div></div><div className="operation-settings-grid"><div className="operation-setting-card"><h3>Saída padrão da operação</h3><p>Usada quando não há hotel fechado no período atual.</p><label>Prestige de saída<select value={defaultDeparture} onChange={(event) => setDefaultDeparture(event.target.value)}><option value="BAHIA">Prestige Waves Bahia</option><option value="SELECTION">Prestige Praia do Forte Selection</option></select></label><button className="button button-secondary" onClick={saveDefault} disabled={saving}>Salvar saída padrão</button></div><form className="operation-setting-card" onSubmit={addClosure}><h3>Fechamento de hotel</h3><p>O sistema bloqueia automaticamente as funções ligadas ao hotel fechado.</p><label>Hotel fechado<select value={closure.hotel} onChange={(event) => changeHotel(event.target.value)}><option value="WAVES_BAHIA">Waves Bahia</option><option value="PRAIA_SELECTION">Praia do Forte Selection</option></select></label><div className="closure-dates"><label>Data inicial<input type="date" value={closure.startDate} onChange={(event) => setClosure({ ...closure, startDate: event.target.value })} required /></label><label>Data final<input type="date" value={closure.endDate} onChange={(event) => setClosure({ ...closure, endDate: event.target.value })} required /></label></div><label>Prestige de saída nesse período<select value={closure.departurePrestige} onChange={(event) => setClosure({ ...closure, departurePrestige: event.target.value })}><option value="BAHIA" disabled={closure.hotel === 'WAVES_BAHIA'}>Prestige Waves Bahia</option><option value="SELECTION" disabled={closure.hotel === 'PRAIA_SELECTION'}>Prestige Praia do Forte Selection</option></select></label><button className="button button-primary" disabled={saving}>{saving && <LoaderCircle className="spin" size={17} />} Adicionar fechamento</button></form></div><div className="closure-list"><h3>Períodos configurados</h3>{closures.length ? closures.map((item) => <article key={item.id}><div><strong>{item.hotel === 'WAVES_BAHIA' ? 'Waves Bahia' : 'Praia do Forte Selection'}</strong><span>{item.startDate.split('-').reverse().join('/')} até {item.endDate.split('-').reverse().join('/')} · saída: {item.departurePrestige === 'BAHIA' ? 'Prestige Waves Bahia' : 'Prestige Praia do Forte Selection'}</span></div><button className="mini-action danger-mini" onClick={() => removeClosure(item)} disabled={saving}>Remover</button></article>) : <p className="hostess-empty">Nenhum fechamento de hotel configurado.</p>}</div>{(settings.activeClosures || []).length > 0 && <div className="operation-active-note"><Building2 size={19} /><span>Hoje: {(settings.activeClosures || []).map((item) => item.hotelLabel).join(', ')} fechado. Saída pelo {settings.departureLabel}.</span></div>}</section>;
}

function LegacySettingsPage({ data, user, token, refresh, notify }) {
  const [editor, setEditor] = useState(null);
  const [resetOpen, setResetOpen] = useState(false);
  const [deletingUser, setDeletingUser] = useState(null);
  const [resetting, setResetting] = useState(false);
  const [deleting, setDeleting] = useState(false);
  if (user.role !== 'ADMIN') return <section className="restricted"><LockKeyhole size={35} /><h1>Acesso restrito</h1><p>Somente administradores podem gerenciar usuários.</p></section>;
  const checkins = new Map((data.attendance || []).map((item) => [item.userId, item]));
  async function resetOperation() {
    setResetting(true);
    try { await api(token, '/api/operation/reset', { method: 'POST' }); await refresh(); setResetOpen(false); notify('Dados operacionais zerados para o dia atual.', 'success'); } catch (error) { notify(error.message, 'error'); } finally { setResetting(false); }
  }
  async function deleteUser() {
    setDeleting(true);
    try { await api(token, `/api/users/${deletingUser.id}`, { method: 'DELETE' }); await refresh(); setDeletingUser(null); notify('Usuário excluído com sucesso.', 'success'); } catch (error) { notify(error.message, 'error'); } finally { setDeleting(false); }
  }
  return <><SectionHeader title="Configurações" description="Gerencie usuários, acessos e presença diária da equipe." action={() => setEditor({})} actionText="Novo usuário" /><section className="panel full-panel"><div className="panel-heading"><div><h2>Usuários cadastrados</h2><p>O administrador pode editar, desativar ou excluir qualquer cadastro.</p></div></div><div className="table-wrap users-table"><table><thead><tr><th>Nome</th><th>Usuário</th><th>Perfil</th><th>Status</th><th>Check-in hoje</th><th>Ações</th></tr></thead><tbody>{data.users.map((item) => { const checkin = checkins.get(item.id); const roleLabel = item.role === 'ADMIN' ? 'Administrador' : item.role === 'MOTORISTA' ? 'Motorista' : item.role === 'HOSTESS' ? 'Hostess' : 'Concierge'; const requiresCheckIn = ['MOTORISTA', 'HOSTESS'].includes(item.role); return <tr key={item.id}><td><div className="name-cell"><Avatar name={item.name} color="blue" /><strong>{item.name}</strong></div></td><td>{item.username}</td><td><span className="role-tag">{roleLabel}</span></td><td><span className={item.active ? 'active-dot' : 'inactive-dot'}>{item.active ? 'Ativo' : 'Inativo'}</span></td><td>{requiresCheckIn ? checkin ? <span className="active-dot">Trabalhando · {time(checkin.checkInAt)}</span> : <span className="inactive-dot">Folga / atestado</span> : '—'}</td><td className="actions-cell"><button className="mini-action" onClick={() => setEditor(item)}>Editar</button>{item.id === user.id ? <span className="current-user-note">Usuário atual</span> : <button className="mini-action danger-mini" onClick={() => setDeletingUser(item)}>Excluir</button>}</td></tr>; })}</tbody></table></div></section><OperationSettingsPanel data={data} token={token} refresh={refresh} notify={notify} /><section className="operation-reset"><div><h2>Zerar dados operacionais</h2><p>Remove tours, convites Waves, filas, atividades, check-ins e indicadores de motoristas. Usuários e cadastros são preservados.</p></div><button className="button button-danger" onClick={() => setResetOpen(true)}>Zerar operação</button></section>{editor && <UserEditorModal key={editor.id || 'new'} account={editor.id ? editor : null} drivers={data.drivers} onClose={() => setEditor(null)} token={token} refresh={refresh} notify={notify} />}{resetOpen && <Modal title="Zerar operação do dia" onClose={() => setResetOpen(false)}><div className="danger-copy"><CircleUserRound size={25} /><p>Esta ação remove tours, convites Waves, filas, histórico, check-ins e contadores. Usuários, consultores, motoristas, carrinhos e destinos permanecem cadastrados.</p></div><div className="modal-actions"><button className="button button-secondary" onClick={() => setResetOpen(false)}>Cancelar</button><button className="button button-danger" onClick={resetOperation} disabled={resetting}>{resetting && <LoaderCircle className="spin" size={17} />} Confirmar e zerar</button></div></Modal>}{deletingUser && <Modal title="Excluir usuário" onClose={() => setDeletingUser(null)}><div className="danger-copy"><CircleUserRound size={25} /><p>Excluir <strong>{deletingUser.name}</strong> removerá seu acesso imediatamente.</p></div><div className="modal-actions"><button className="button button-secondary" onClick={() => setDeletingUser(null)}>Cancelar</button><button className="button button-danger" onClick={deleteUser} disabled={deleting}>{deleting && <LoaderCircle className="spin" size={17} />} Excluir usuário</button></div></Modal>}</>;
}

function SettingsPage({ data, user, token, refresh, notify }) {
  const [editor, setEditor] = useState(null);
  const [resetOpen, setResetOpen] = useState(false);
  const [deletingUser, setDeletingUser] = useState(null);
  const [resetting, setResetting] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const canManageUsers = can(user, 'MANAGE_USERS');
  const canManageSettings = can(user, 'MANAGE_SETTINGS');
  const catalog = permissionCatalog(data);
  const checkins = new Map((data.attendance || []).map((item) => [item.userId, item]));

  async function resetOperation() {
    setResetting(true);
    try {
      await api(token, '/api/operation/reset', { method: 'POST' });
      await refresh();
      setResetOpen(false);
      notify('Dados operacionais zerados para o dia atual.', 'success');
    } catch (error) {
      notify(error.message, 'error');
    } finally {
      setResetting(false);
    }
  }

  async function deleteUser() {
    setDeleting(true);
    try {
      await api(token, `/api/users/${deletingUser.id}`, { method: 'DELETE' });
      await refresh();
      setDeletingUser(null);
      notify('Usuário excluído com sucesso.', 'success');
    } catch (error) {
      notify(error.message, 'error');
    } finally {
      setDeleting(false);
    }
  }

  if (!canManageUsers && !canManageSettings) {
    return <section className="restricted"><LockKeyhole size={35} /><h1>Acesso restrito</h1><p>Você não possui permissão para alterar as configurações da operação.</p></section>;
  }

  return <>
    <SectionHeader title="Configurações" description="Gerencie usuários, acessos e presença diária da equipe." action={canManageUsers ? () => setEditor({}) : undefined} actionText="Novo usuário" />
    {canManageUsers && <section className="panel full-panel">
      <div className="panel-heading"><div><h2>Usuários cadastrados</h2><p>Defina perfil e permissões específicas para cada conta.</p></div></div>
      <div className="table-wrap users-table"><table><thead><tr><th>Nome</th><th>Usuário</th><th>Perfil</th><th>Acessos</th><th>Status</th><th>Check-in hoje</th><th>Ações</th></tr></thead><tbody>{data.users.map((item) => {
        const checkin = checkins.get(item.id);
        const requiresCheckIn = can(item, 'CHECK_IN');
        const userPermissions = selectedPermissionsForAccount(item, catalog);
        return <tr key={item.id}><td><div className="name-cell"><Avatar name={item.name} color="blue" /><strong>{item.name}</strong></div></td><td>{item.username}</td><td><span className="role-tag">{roleLabel(item.role)}</span></td><td><PermissionSummary permissions={userPermissions} catalog={catalog} fallbackRole={item.role} /></td><td><span className={item.active ? 'active-dot' : 'inactive-dot'}>{item.active ? 'Ativo' : 'Inativo'}</span></td><td>{requiresCheckIn ? checkin ? <span className="active-dot">Trabalhando · {time(checkin.checkInAt)}</span> : <span className="inactive-dot">Folga / atestado</span> : '—'}</td><td className="actions-cell"><button className="mini-action" onClick={() => setEditor(item)}>Editar</button>{item.id === user.id ? <span className="current-user-note">Usuário atual</span> : <button className="mini-action danger-mini" onClick={() => setDeletingUser(item)}>Excluir</button>}</td></tr>;
      })}</tbody></table></div>
    </section>}
    {canManageSettings && <>
      <OperationSettingsPanel data={data} token={token} refresh={refresh} notify={notify} />
      <section className="operation-reset"><div><h2>Zerar dados operacionais</h2><p>Remove tours, convites Waves, filas, atividades, check-ins e indicadores de motoristas. Usuários e cadastros são preservados.</p></div><button className="button button-danger" onClick={() => setResetOpen(true)}>Zerar operação</button></section>
    </>}
    {editor && canManageUsers && <UserEditorModal key={editor.id || 'new'} account={editor.id ? editor : null} drivers={data.drivers} permissionCatalog={catalog} onClose={() => setEditor(null)} token={token} refresh={refresh} notify={notify} />}
    {resetOpen && canManageSettings && <Modal title="Zerar operação do dia" onClose={() => setResetOpen(false)}><div className="danger-copy"><CircleUserRound size={25} /><p>Esta ação remove tours, convites Waves, filas, histórico, check-ins e contadores. Usuários, consultores, motoristas, carrinhos e destinos permanecem cadastrados.</p></div><div className="modal-actions"><button className="button button-secondary" onClick={() => setResetOpen(false)}>Cancelar</button><button className="button button-danger" onClick={resetOperation} disabled={resetting}>{resetting && <LoaderCircle className="spin" size={17} />} Confirmar e zerar</button></div></Modal>}
    {deletingUser && canManageUsers && <Modal title="Excluir usuário" onClose={() => setDeletingUser(null)}><div className="danger-copy"><CircleUserRound size={25} /><p>Excluir <strong>{deletingUser.name}</strong> removerá seu acesso imediatamente.</p></div><div className="modal-actions"><button className="button button-secondary" onClick={() => setDeletingUser(null)}>Cancelar</button><button className="button button-danger" onClick={deleteUser} disabled={deleting}>{deleting && <LoaderCircle className="spin" size={17} />} Excluir usuário</button></div></Modal>}
  </>;
}

function CreateTourModal({ data, onClose, token, refresh, notify }) {
  const [form, setForm] = useState({ quantity: '0', selfGeanQuantity: '0', wave: 'WAVE_1' });
  const [saving, setSaving] = useState(false);
  async function submit(event) {
    event.preventDefault(); setSaving(true);
    try { await api(token, '/api/tours', { method: 'POST', body: JSON.stringify({ ...form, quantity: Number(form.quantity), selfGeanQuantity: Number(form.selfGeanQuantity) }) }); await refresh(); notify('Quantidades de tours registradas.', 'success'); onClose(); } catch (error) { notify(error.message, 'error'); } finally { setSaving(false); }
  }
  return <Modal title="Cadastrar quantidades de tours" onClose={onClose}><form className="modal-form" onSubmit={submit}><label>Quantidade de tours<input type="number" min="0" max="30" value={form.quantity} onChange={(event) => setForm({ ...form, quantity: event.target.value })} required /></label><label>Quantidade de Self Gen<input type="number" min="0" max="30" value={form.selfGeanQuantity} onChange={(event) => setForm({ ...form, selfGeanQuantity: event.target.value })} required /></label><label>Ola do tour<select value={form.wave} onChange={(event) => setForm({ ...form, wave: event.target.value })}>{Object.entries(WAVES).map(([key, wave]) => <option key={key} value={key}>{wave.label} · saída às {wave.tourTime}</option>)}</select></label><div className="role-help">Tours e Self Gen são contagens separadas. A família, hóspedes, consultor, carrinhos e motoristas não são informados nesta etapa.</div><button className="button button-primary" disabled={saving}>{saving && <LoaderCircle className="spin" size={17} />} Registrar quantidades</button></form></Modal>;
}

function CreateTransferModal({ user, onClose, token, refresh, notify }) {
  const [form, setForm] = useState({ groupName: '', people: '', conciergeName: '', wave: 'WAVE_1' });
  const [saving, setSaving] = useState(false);
  const schedule = WAVES[form.wave];
  async function submit(event) {
    event.preventDefault(); setSaving(true);
    try { await api(token, '/api/transfers', { method: 'POST', body: JSON.stringify({ ...form, people: Number(form.people) }) }); await refresh(); notify('Convite Waves agendado.', 'success'); onClose(); } catch (error) { notify(error.message, 'error'); } finally { setSaving(false); }
  }
  const concierge = user.role === 'CONCIERGE';
  return <Modal title="Novo convite do Waves" onClose={onClose}><div className="transfer-modal-route"><Route size={24} /><span>Prestige Waves Bahia <ChevronRight size={16} /> Praia do Forte</span></div><form className="modal-form" onSubmit={submit}><label>Família ou casal convidado<input value={form.groupName} onChange={(event) => setForm({ ...form, groupName: event.target.value })} placeholder="Ex.: Casal de Maria" required /></label><label>Quantidade de pessoas convidadas<input type="number" min="1" max="48" value={form.people} onChange={(event) => setForm({ ...form, people: event.target.value })} required /></label>{concierge ? <div className="role-help">Convite registrado em seu nome: <strong>{user.name}</strong>.</div> : <label>Concierge responsável<input value={form.conciergeName} onChange={(event) => setForm({ ...form, conciergeName: event.target.value })} placeholder="Nome do concierge" required /></label>}<label>Convite para a Ola<select value={form.wave} onChange={(event) => setForm({ ...form, wave: event.target.value })}>{Object.entries(WAVES).map(([key, wave]) => <option key={key} value={key}>{wave.label} · tour às {wave.tourTime}</option>)}</select></label><div className="schedule-callout"><strong>Traslado às {schedule.transferTime}</strong><span>Chegada prevista antes do tour das {schedule.tourTime}. Caso não venha, registre a desistência antes do traslado.</span></div><button className="button button-primary" disabled={saving}>{saving && <LoaderCircle className="spin" size={17} />} Agendar convite</button></form></Modal>;
}

function TransferActionModal({ transfer, action, onClose, token, refresh, notify }) {
  const isStart = action === 'start';
  const isWithdraw = action === 'withdraw';
  const [saving, setSaving] = useState(false);
  async function confirm() {
    setSaving(true);
    try { await api(token, `/api/transfers/${transfer.id}/action`, { method: 'POST', body: JSON.stringify({ action }) }); await refresh(); notify(isWithdraw ? 'Desistência registrada.' : isStart ? 'Traslado iniciado.' : 'Chegada ao Praia do Forte registrada.', 'success'); onClose(); } catch (error) { notify(error.message, 'error'); } finally { setSaving(false); }
  }
  return <Modal title={isWithdraw ? 'Registrar desistência' : isStart ? 'Iniciar traslado do Waves' : 'Confirmar chegada ao Praia'} onClose={onClose}><div className="action-tour-summary"><Avatar name={transfer.groupName} color="teal" /><div><strong>{transfer.groupName}</strong><span>{transfer.people} pessoas · {WAVES[transfer.wave]?.label} · {transfer.scheduledTime}</span></div></div><p className="modal-intro">{isWithdraw ? 'Confirme que esta família ou casal não participará do convite Waves.' : isStart ? 'Registre a saída do concierge com os hóspedes do Prestige Waves Bahia.' : 'Confirme a chegada ao Prestige Praia do Forte para o convite do tour.'}</p><button className={classNames('button', isWithdraw ? 'button-danger' : 'button-primary', 'modal-confirm')} onClick={confirm} disabled={saving}>{saving && <LoaderCircle className="spin" size={17} />} <Check size={17} /> {isWithdraw ? 'Confirmar desistência' : 'Confirmar'}</button></Modal>;
}

function ActionModal({ tour, action, data, user, onClose, token, refresh, notify }) {
  const meta = actionMeta[action];
  const isWithdraw = action === 'withdraw';
  const isQuantityTour = Boolean(tour.requiresDetails);
  const homeDrivers = (tour.allocations || []).filter((item) => item.homeDecision === 'AGUARDOU_NA_CASA');
  const requiredHomeCarts = tour.requiredCartCount || (tour.allocations || []).length;
  const incomingDriversNeeded = Math.max(0, requiredHomeCarts - homeDrivers.length);
  const [allocations, setAllocations] = useState(() => meta.allocations ? Array.from({ length: meta.homeJoin ? Math.max(1, incomingDriversNeeded) : action === 'pickup-home' ? Math.max(1, requiredHomeCarts) : 1 }, () => ({ driverId: '' })) : []);
  const pendingArrivals = (tour.allocations || []).filter((item) => !item.homeDecision);
  const [homeDriverId, setHomeDriverId] = useState(() => pendingArrivals.find((item) => item.driverId === user?.driverId)?.driverId || pendingArrivals[0]?.driverId || '');
  const [homeDecision, setHomeDecision] = useState('AGUARDOU_NA_CASA');
  const [destinationId, setDestinationId] = useState(tour.destinationId || '');
  const [consultantId, setConsultantId] = useState(tour.consultantId || '');
  const [saving, setSaving] = useState(false);
  const activeConsultants = (data.consultants || []).filter((consultant) => consultant.active);
  const drivers = data.drivers.filter((driver) => driver.status === 'DISPONIVEL' && !driver.hostessAvailable);
  const currentTourDriverIds = new Set((tour.allocations || []).map((item) => item.driverId));
  const driverIdsOnWayToHome = new Set((data.tours || []).filter((item) => item.status === 'EM_TOUR' && item.phase !== 'Casa → Galeria').flatMap((item) => (item.allocations || []).map((allocation) => allocation.driverId)));
  const driversOnWayToHome = data.drivers.filter((driver) => driverIdsOnWayToHome.has(driver.id) && !currentTourDriverIds.has(driver.id));
  const updateAllocation = (index, field, value) => setAllocations((current) => current.map((allocation, itemIndex) => itemIndex === index ? { ...allocation, [field]: value } : allocation));
  async function submit(event) {
    event.preventDefault(); setSaving(true);
    const body = { action, allocations, destinationId, driverId: homeDriverId, homeDecision, consultantId };
    try { await api(token, `/api/tours/${tour.id}/action`, { method: 'POST', body: JSON.stringify(body) }); await refresh(); notify(isWithdraw ? 'Desistência registrada no histórico.' : `${meta.label} registrado.`, 'success'); onClose(); } catch (error) { notify(error.message, 'error'); } finally { setSaving(false); }
  }
  return <Modal title={meta.title} onClose={onClose}><div className="action-tour-summary"><Avatar name={tour.groupName} color="teal" /><div><strong>{tour.groupName}</strong><span>{isQuantityTour ? 'Tour registrado por quantidade' : STATUS[tour.status]?.label}</span></div></div><p className="modal-intro">{meta.text}</p><form className="modal-form" onSubmit={submit}>{action === 'start' && isQuantityTour && <label>Consultor que está saindo<select value={consultantId} onChange={(event) => setConsultantId(event.target.value)} required><option value="">Selecione o consultor</option>{activeConsultants.map((consultant) => <option value={consultant.id} key={consultant.id}>{consultant.name}</option>)}</select>{!activeConsultants.length && <small className="field-help">Não há consultor ativo cadastrado. Peça ao administrador para cadastrar um em Consultores.</small>}</label>}{meta.destination && <label>Destino final<select value={destinationId} onChange={(event) => setDestinationId(event.target.value)} required><option value="">Selecione o destino</option>{data.destinations.filter((item) => item.active).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>}{meta.allocations && <div className="allocation-form"><div className="allocation-title"><span>{meta.homeJoin ? 'Motorista a caminho da Casa' : 'Motoristas'}</span><small>{meta.homeJoin ? `Falta ${incomingDriversNeeded} motorista${incomingDriversNeeded === 1 ? '' : 's'} para completar ${requiredHomeCarts} carrinhos` : action === 'pickup-home' && requiredHomeCarts > 1 ? `Este casal precisa de ${requiredHomeCarts} motoristas` : 'Um carrinho disponível será reservado para cada motorista'}</small></div><p className="allocation-help">{meta.homeJoin ? 'Dê prioridade a quem já está em tour a caminho da Casa. Depois de liberado do grupo atual, selecione-o para completar os carrinhos deste casal.' : action === 'pickup-home' && requiredHomeCarts > 1 ? `Selecione os ${requiredHomeCarts} motoristas necessários para este casal. O sistema não permite iniciar a busca com menos carrinhos.` : 'Informe somente o nome do motorista. Não é necessário informar família, casal, hóspedes ou carrinho.'}</p>{meta.homeJoin && driversOnWayToHome.length > 0 && <div className="role-help"><strong>PRIORIDADE DE CHAMADA:</strong> {driversOnWayToHome.map((driver) => driver.name).join(', ')} já está{driversOnWayToHome.length === 1 ? '' : 'ão'} em tour a caminho da Casa. Ao ficar disponível, use este motorista primeiro.</div>}{allocations.map((allocation, index) => <div className="allocation-row" key={index}><label>Motorista<select value={allocation.driverId} onChange={(event) => updateAllocation(index, 'driverId', event.target.value)} required><option value="">Selecione</option>{drivers.filter((driver) => driver.id === allocation.driverId || !allocations.some((item, itemIndex) => itemIndex !== index && item.driverId === driver.id)).map((driver) => <option value={driver.id} key={driver.id}>{driver.name}</option>)}</select></label>{!meta.homeJoin && allocations.length > 1 && <button type="button" className="remove-allocation" onClick={() => setAllocations((current) => current.filter((_, itemIndex) => itemIndex !== index))}>Remover</button>}</div>)}<div className="allocation-footer"><span>{allocations.filter((item) => item.driverId).length} motorista{allocations.filter((item) => item.driverId).length === 1 ? '' : 's'} selecionado{allocations.filter((item) => item.driverId).length === 1 ? '' : 's'}</span>{!meta.homeJoin && <button type="button" className="text-button" onClick={() => setAllocations((current) => [...current, { driverId: '' }])}><Plus size={15} /> Adicionar carrinho</button>}</div></div>}{meta.individualArrival && <div className="allocation-form"><div className="allocation-title"><span>Registro individual do motorista</span><small>{pendingArrivals.length} pendente{pendingArrivals.length === 1 ? '' : 's'}</small></div><label>Motorista<select value={homeDriverId} onChange={(event) => setHomeDriverId(event.target.value)} required>{pendingArrivals.map((item) => { const driver = data.drivers.find((candidate) => candidate.id === item.driverId); return <option value={item.driverId} key={item.driverId}>{driver?.name || 'Motorista'}</option>; })}</select></label><label>Ao chegar na Casa<select value={homeDecision} onChange={(event) => setHomeDecision(event.target.value)}><option value="AGUARDOU_NA_CASA">Permaneceu aguardando com a família</option><option value="DEIXOU_NA_CASA">Deixou a família e voltou ao Prestige</option></select></label></div>}<button className={classNames('button', meta.danger ? 'button-danger' : 'button-primary')} disabled={saving || (meta.individualArrival && !homeDriverId) || (action === 'start' && isQuantityTour && (!consultantId || !activeConsultants.length))}>{saving && <LoaderCircle className="spin" size={17} />} <Check size={17} /> {isWithdraw ? 'Confirmar desistência' : 'Confirmar'}</button></form></Modal>;
}

function Modal({ title, onClose, children }) {
  return <div className="modal-backdrop" role="presentation" onMouseDown={onClose}><section className="modal" role="dialog" aria-modal="true" aria-label={title} onMouseDown={(event) => event.stopPropagation()}><div className="modal-header"><h2>{title}</h2><button onClick={onClose} aria-label="Fechar"><X size={21} /></button></div>{children}</section></div>;
}

function ConsultantDriverPanel() {
  const [board, setBoard] = useState({ drivers: [], operationDate: '' });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const loadBoard = useCallback(async () => {
    try {
      const payload = await api('', '/api/public/driver-status');
      setBoard(payload); setError('');
    } catch (requestError) {
      setError(requestError.message || 'Não foi possível atualizar o painel.');
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => {
    loadBoard();
    const timer = window.setInterval(loadBoard, 30000);
    return () => window.clearInterval(timer);
  }, [loadBoard]);
  return <main className="consultant-public-page">
    <header className="consultant-public-header"><Logo /><a href="/" className="public-login-link"><LockKeyhole size={16} /> Acesso da equipe</a></header>
    <section className="consultant-public-hero"><span>PAINEL DOS CONSULTORES</span><h1>Status dos motoristas</h1><p>Consulta pública, sem login. Atualização automática a cada 30 segundos.</p></section>
    <section className="consultant-public-summary"><CarFront size={28} /><div><strong>{board.drivers.length}</strong><span>motorista{board.drivers.length === 1 ? '' : 's'} ativo{board.drivers.length === 1 ? '' : 's'}</span></div><small>Operação: {board.operationDate || '—'}</small></section>
    {error && <div className="consultant-public-error" role="alert">{error}</div>}
    {loading ? <div className="public-loading"><LoaderCircle className="spin" size={30} /> Carregando status dos motoristas...</div> : <section className="consultant-driver-grid" aria-live="polite">{board.drivers.length ? board.drivers.map((driver) => <article className="consultant-driver-status" key={driver.name}><Avatar name={driver.name} color="photo" /><div><strong>{driver.name}</strong><span>{driver.locationLabel || DRIVER_STATUS[driver.status]?.label || 'Localização não informada'}</span><span>Atualizado: {time(driver.lastActivity)}</span></div><StatusPill driver status={driver.status} /></article>) : <div className="empty-state">Nenhum motorista ativo cadastrado.</div>}</section>}
  </main>;
}

function App() {
  const [token, setToken] = useState(() => localStorage.getItem('iberostar-tour-token') || '');
  const [user, setUser] = useState(null);
  const [data, setData] = useState(null);
  const [page, setPage] = useState('dashboard');
  const [menuOpen, setMenuOpen] = useState(false);
  const [modal, setModal] = useState(null);
  const [notice, setNotice] = useState(null);
  const [loading, setLoading] = useState(Boolean(token));
  const [notificationPermission, setNotificationPermission] = useState(() => 'Notification' in window ? window.Notification.permission : 'unsupported');

  const notify = (message, type = 'success') => { setNotice({ message, type }); window.setTimeout(() => setNotice(null), 4000); };
  const refresh = useCallback(async () => {
    const payload = await api(token, '/api/bootstrap');
    setUser(payload.user); setData({ ...(payload.data || {}), permissionsCatalog: payload.permissionsCatalog || payload.data?.permissionsCatalog, rolePermissionDefaults: payload.rolePermissionDefaults || payload.data?.rolePermissionDefaults }); setPage((current) => canAccessPage(payload.user, current) ? current : firstAccessiblePage(payload.user));
  }, [token]);
  useEffect(() => {
    if (!('serviceWorker' in navigator)) return undefined;
    navigator.serviceWorker.register('/service-worker.js').catch(() => undefined);
    return undefined;
  }, []);
  useEffect(() => { if (!token) { setLoading(false); return; } setLoading(true); refresh().catch(() => { localStorage.removeItem('iberostar-tour-token'); setToken(''); }).finally(() => setLoading(false)); }, [token, refresh]);
  useEffect(() => {
    if (!token) return undefined;
    const timer = window.setInterval(() => { refresh().catch(() => undefined); }, 30000);
    return () => window.clearInterval(timer);
  }, [token, refresh]);
  const registerPushSubscription = useCallback(async ({ requestPermission = false, sendTest = false } = {}) => {
    if (!token || !('Notification' in window) || !('serviceWorker' in navigator) || !('PushManager' in window)) return { supported: false };
    let permission = window.Notification.permission;
    if (requestPermission && permission === 'default') permission = await window.Notification.requestPermission();
    setNotificationPermission(permission);
    if (permission !== 'granted') return { supported: true, configured: true, permission };
    const config = await api(token, '/api/push/config');
    if (!config.enabled || !config.publicKey) return { supported: true, configured: false, permission };
    const registration = await navigator.serviceWorker.ready;
    let subscription = await registration.pushManager.getSubscription();
    if (!subscription) {
      if (!requestPermission) return { supported: true, configured: true, permission, subscribed: false };
      subscription = await registration.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: urlBase64ToUint8Array(config.publicKey) });
    }
    await api(token, '/api/push/subscription', { method: 'PUT', body: JSON.stringify({ subscription: subscription.toJSON() }) });
    if (sendTest) await api(token, '/api/push/test', { method: 'POST' });
    return { supported: true, configured: true, permission, subscribed: true };
  }, [token]);
  useEffect(() => {
    if (!token || !('Notification' in window) || window.Notification.permission !== 'granted') return;
    registerPushSubscription().catch(() => undefined);
  }, [token, registerPushSubscription]);
  async function requestNotifications() {
    if (!('Notification' in window) || !('serviceWorker' in navigator) || !('PushManager' in window)) {
      notify('Este navegador não oferece notificações push neste aparelho.', 'error');
      return;
    }
    if (window.Notification.permission === 'denied') {
      setNotificationPermission('denied');
      notify('As notificações foram bloqueadas. Libere-as nas configurações do navegador para este site.', 'error');
      return;
    }
    try {
      const result = await registerPushSubscription({ requestPermission: true, sendTest: true });
      if (!result.configured) {
        notify('O servidor ainda precisa das chaves VAPID para ativar o push.', 'error');
        return;
      }
      if (result.permission !== 'granted') {
        notify('A permissão de notificações não foi concedida.', 'error');
        return;
      }
      notify('Notificações push ativadas. Você receberá avisos mesmo com o navegador fechado.', 'success');
    } catch (error) {
      notify(error.message || 'Não foi possível ativar as notificações push neste navegador.', 'error');
    }
  }
  function login(nextToken, nextUser) { localStorage.setItem('iberostar-tour-token', nextToken); setUser(nextUser); setToken(nextToken); }
  async function signOut() {
    try {
      const registration = await navigator.serviceWorker?.getRegistration();
      const subscription = await registration?.pushManager.getSubscription();
      if (subscription) {
        await api(token, '/api/push/subscription', { method: 'DELETE', body: JSON.stringify({ endpoint: subscription.endpoint }) });
        await subscription.unsubscribe();
      }
    } catch { /* The user can still safely sign out if the device is offline. */ }
    try { await api(token, '/api/auth/logout', { method: 'POST' }); } catch { /* session may already be gone */ }
    localStorage.removeItem('iberostar-tour-token'); setToken(''); setUser(null); setData(null);
  }
  const content = useMemo(() => {
    if (!data || !user) return null;
    const openAction = (tour, action) => setModal({ kind: 'action', tour, action });
    const openCreate = () => setModal({ kind: 'create' });
    const openTransfer = () => setModal({ kind: 'transfer' });
    const openTransferAction = (transfer, action) => setModal({ kind: 'transfer-action', transfer, action });
    const activePage = canAccessPage(user, page) ? page : firstAccessiblePage(user);
    const hostessWorkspace = user.role === 'HOSTESS' && canAny(user, ['CHECK_IN', 'MANAGE_TOUR_QUANTITIES', 'REQUEST_HOSTESS_CAR']);
    if (!activePage) return <section className="restricted"><LockKeyhole size={35} /><h1>Sem acesso liberado</h1><p>Peça ao administrador para selecionar as permissões da sua conta.</p></section>;
    if (activePage === 'dashboard' && hostessWorkspace) return <HostessDashboard data={data} user={user} token={token} refresh={refresh} notify={notify} />;
    if (activePage === 'dashboard') return <Dashboard data={data} user={user} token={token} refresh={refresh} notify={notify} onAction={openAction} onCreate={openCreate} onCreateTransfer={openTransfer} onTransferAction={openTransferAction} setPage={setPage} />;
    if (['prestige', 'tours', 'home', 'destinations'].includes(activePage)) return <OperationalPage page={activePage} data={data} user={user} onAction={openAction} onCreate={openCreate} />;
    if (activePage === 'transfers') return user.role === 'CONCIERGE' && data.operationSettings?.conciergePanelClosed ? <ConciergeClosedPage data={data} /> : <TransfersPage data={data} user={user} onCreate={openTransfer} onAction={openTransferAction} />;
    if (activePage === 'gallery') return <GalleryPage data={data} user={user} onAction={openAction} />;
    if (activePage === 'drivers') return <DriversPage data={data} user={user} token={token} refresh={refresh} notify={notify} />;
    if (activePage === 'consultants') return <ConsultantsPage data={data} user={user} token={token} refresh={refresh} notify={notify} />;
    if (activePage === 'carts') return <CartsPage data={data} />;
    if (activePage === 'history') return <HistoryPage data={data} />;
    if (activePage === 'reports') return <ReportsPage data={data} />;
    if (activePage === 'settings') return <SettingsPage data={data} user={user} token={token} refresh={refresh} notify={notify} />;
    return null;
  }, [data, user, page, token]);
  if (!token) return <Login onLogin={login} />;
  if (loading || !data || !user) return <div className="loading-screen"><LoaderCircle className="spin" size={34} /><span>Carregando operação...</span></div>;
  return <div className="app-shell"><Sidebar user={user} page={page} setPage={setPage} signOut={signOut} open={menuOpen} setOpen={setMenuOpen} operationSettings={data.operationSettings} /><div className="app-content"><Topbar user={user} setMenuOpen={setMenuOpen} notificationPermission={notificationPermission} onNotifications={requestNotifications} /><main className="content-area">{user.role === 'MOTORISTA' && can(user, 'CHECK_IN') && <CheckInCard data={data} user={user} token={token} refresh={refresh} notify={notify} />}{content}</main></div>{menuOpen && <button className="sidebar-scrim" aria-label="Fechar menu" onClick={() => setMenuOpen(false)} />}{notice && <div className={classNames('toast', notice.type)}>{notice.type === 'success' ? <Check size={19} /> : <X size={19} />}{notice.message}</div>}{modal?.kind === 'create' && <CreateTourModal data={data} onClose={() => setModal(null)} token={token} refresh={refresh} notify={notify} />}{modal?.kind === 'transfer' && <CreateTransferModal user={user} onClose={() => setModal(null)} token={token} refresh={refresh} notify={notify} />}{modal?.kind === 'action' && <ActionModal {...modal} data={data} user={user} onClose={() => setModal(null)} token={token} refresh={refresh} notify={notify} />}{modal?.kind === 'transfer-action' && <TransferActionModal {...modal} onClose={() => setModal(null)} token={token} refresh={refresh} notify={notify} />}{<MobileNav page={page} setPage={setPage} user={user} operationSettings={data.operationSettings} />}</div>;
}

function Root() {
  return window.location.pathname.startsWith('/consultores') ? <ConsultantDriverPanel /> : <App />;
}

createRoot(document.getElementById('root')).render(<React.StrictMode><Root /></React.StrictMode>);

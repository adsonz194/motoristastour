import { createServer } from 'node:http';
import { readFile, writeFile, mkdir, access } from 'node:fs/promises';
import { createHash, randomBytes, scrypt, timingSafeEqual } from 'node:crypto';
import { promisify } from 'node:util';
import { extname, join, normalize } from 'node:path';
import { fileURLToPath } from 'node:url';

const scryptAsync = promisify(scrypt);
const root = fileURLToPath(new URL('.', import.meta.url));
const dataDir = join(root, 'data');
const databasePath = join(dataDir, 'database.json');
const distDir = join(root, 'dist');
const sessions = new Map();
const port = Number(process.env.PORT || 4174);

const roles = Object.freeze({ ADMIN: 'ADMIN', MOTORISTA: 'MOTORISTA', HOSTESS: 'HOSTESS' });
const tourStates = Object.freeze({
  DISPONIVEL: 'DISPONIVEL',
  EM_TOUR: 'EM_TOUR',
  NA_CASA: 'NA_CASA',
  AGUARDANDO_CASA: 'AGUARDANDO_CASA',
  NA_GALERIA: 'NA_GALERIA',
  EM_APRESENTACAO: 'EM_APRESENTACAO',
  AGUARDANDO_DESTINO: 'AGUARDANDO_DESTINO',
  EM_DESTINO_FINAL: 'EM_DESTINO_FINAL',
  CONCLUIDO: 'CONCLUIDO'
});

const driverStates = Object.freeze({
  DISPONIVEL: 'DISPONIVEL',
  EM_TOUR: 'EM_TOUR',
  CASA: 'CASA',
  GALERIA: 'GALERIA',
  DESTINO_FINAL: 'DESTINO_FINAL'
});

const initialPasswordHash = 'c75658f843ab803ffbeeee35e0af7299:4d6dd57c1f333e36a98469f931d3ef728178f675b2a3d80e9f750675ab71afc976731e7a49d8b55e705e1d118631d62a9c16d49403b6c5fb0e2c2d2b04a24f5c';
const now = () => new Date().toISOString();
const id = (prefix) => `${prefix}_${randomBytes(6).toString('hex')}`;

function seedDatabase() {
  const timestamp = now();
  return {
    users: [{
      id: 'user_admin', username: 'adson.gonzalez', name: 'Administrador', role: roles.ADMIN,
      active: true, passwordHash: initialPasswordHash, createdAt: timestamp
    }],
    consultants: [
      { id: 'con_yasmin', name: 'Yasmin', active: true },
      { id: 'con_rafael', name: 'Rafael', active: true },
      { id: 'con_lucas', name: 'Lucas', active: true },
      { id: 'con_fernanda', name: 'Fernanda', active: true },
      { id: 'con_juliana', name: 'Juliana', active: true }
    ],
    drivers: [
      { id: 'drv_carlos', name: 'Carlos', active: true, status: driverStates.EM_TOUR, toursStarted: 5, homePickups: 2, lastActivity: timestamp },
      { id: 'drv_joao', name: 'João', active: true, status: driverStates.EM_TOUR, toursStarted: 4, homePickups: 1, lastActivity: timestamp },
      { id: 'drv_marcos', name: 'Marcos', active: true, status: driverStates.DISPONIVEL, toursStarted: 3, homePickups: 0, lastActivity: timestamp },
      { id: 'drv_pedro', name: 'Pedro', active: true, status: driverStates.CASA, toursStarted: 2, homePickups: 1, lastActivity: timestamp },
      { id: 'drv_ricardo', name: 'Ricardo', active: true, status: driverStates.GALERIA, toursStarted: 3, homePickups: 0, lastActivity: timestamp }
    ],
    carts: [
      { id: 'cart_01', name: 'Carrinho 01', capacity: 6, status: 'EM_USO' },
      { id: 'cart_02', name: 'Carrinho 02', capacity: 6, status: 'EM_USO' },
      { id: 'cart_03', name: 'Carrinho 03', capacity: 6, status: 'DISPONIVEL' },
      { id: 'cart_04', name: 'Carrinho 04', capacity: 6, status: 'EM_USO' },
      { id: 'cart_05', name: 'Carrinho 05', capacity: 6, status: 'EM_USO' }
    ],
    destinations: [
      { id: 'dest_prestige', name: 'Prestige Praia do Forte', active: true },
      { id: 'dest_waves', name: 'Prestige Waves Bahia', active: true },
      { id: 'dest_lobby', name: 'Lobby principal', active: true },
      { id: 'dest_villas', name: 'Villas', active: true }
    ],
    tours: [
      {
        id: 'tour_yasmin', groupName: 'Família de Yasmin', people: 8, selfGuide: false, consultantId: 'con_yasmin',
        status: tourStates.EM_TOUR, phase: 'Golf', createdAt: timestamp, updatedAt: timestamp,
        allocations: [
          { driverId: 'drv_carlos', cartId: 'cart_01', seats: 6, arrived: true },
          { driverId: 'drv_joao', cartId: 'cart_02', seats: 2, arrived: true }
        ]
      },
      {
        id: 'tour_rafael', groupName: 'Casal de Rafael', people: 2, selfGuide: true, consultantId: 'con_rafael',
        status: tourStates.DISPONIVEL, phase: 'Prestige Praia do Forte', createdAt: timestamp, updatedAt: timestamp, allocations: []
      },
      {
        id: 'tour_lucas', groupName: 'Família de Lucas', people: 5, selfGuide: false, consultantId: 'con_lucas',
        status: tourStates.AGUARDANDO_CASA, phase: 'Casa', createdAt: timestamp, updatedAt: timestamp, allocations: []
      },
      {
        id: 'tour_fernanda', groupName: 'Casal de Fernanda', people: 2, selfGuide: false, consultantId: 'con_fernanda',
        status: tourStates.NA_GALERIA, phase: 'Galeria', createdAt: timestamp, updatedAt: timestamp,
        allocations: [{ driverId: 'drv_ricardo', cartId: 'cart_05', seats: 2, arrived: true }]
      },
      {
        id: 'tour_juliana', groupName: 'Família de Juliana', people: 4, selfGuide: true, consultantId: 'con_juliana',
        status: tourStates.EM_APRESENTACAO, phase: 'Galeria', createdAt: timestamp, updatedAt: timestamp, allocations: []
      },
      {
        id: 'tour_marcela', groupName: 'Família de Marcela', people: 6, selfGuide: false, consultantId: 'con_yasmin',
        status: tourStates.AGUARDANDO_DESTINO, phase: 'Galeria', destinationId: 'dest_prestige', createdAt: timestamp, updatedAt: timestamp, allocations: []
      },
      {
        id: 'tour_bruno', groupName: 'Casal de Bruno', people: 2, selfGuide: false, consultantId: 'con_rafael',
        status: tourStates.DISPONIVEL, phase: 'Prestige Praia do Forte', createdAt: timestamp, updatedAt: timestamp, allocations: []
      }
    ],
    activities: [
      { id: 'act_1', at: timestamp, userName: 'Sistema', message: 'Painel operacional iniciado', previous: null, next: null },
      { id: 'act_2', at: timestamp, userName: 'Sistema', message: 'Família de Yasmin está no roteiro do tour', tourId: 'tour_yasmin', previous: 'DISPONIVEL', next: 'EM_TOUR' },
      { id: 'act_3', at: timestamp, userName: 'Sistema', message: 'Família de Marcela aguarda destino final', tourId: 'tour_marcela', previous: 'EM_APRESENTACAO', next: 'AGUARDANDO_DESTINO' }
    ]
  };
}

async function database() {
  try {
    return JSON.parse(await readFile(databasePath, 'utf8'));
  } catch {
    const seeded = seedDatabase();
    await mkdir(dataDir, { recursive: true });
    await writeFile(databasePath, JSON.stringify(seeded, null, 2));
    return seeded;
  }
}

async function save(db) {
  await writeFile(databasePath, JSON.stringify(db, null, 2));
}

async function hashPassword(password, salt = randomBytes(16).toString('hex')) {
  const derived = await scryptAsync(password, salt, 64);
  return `${salt}:${Buffer.from(derived).toString('hex')}`;
}

async function passwordMatches(password, stored) {
  const [salt, expected] = String(stored || '').split(':');
  if (!salt || !expected) return false;
  const derived = await scryptAsync(password, salt, 64);
  const actual = Buffer.from(derived).toString('hex');
  return actual.length === expected.length && timingSafeEqual(Buffer.from(actual), Buffer.from(expected));
}

function sanitizeUser(user) {
  const { passwordHash, ...safe } = user;
  return safe;
}

function safeDatabase(db) {
  return { ...db, users: db.users.map(sanitizeUser) };
}

function json(res, status, body) {
  res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8' });
  res.end(JSON.stringify(body));
}

async function body(req) {
  let raw = '';
  for await (const chunk of req) raw += chunk;
  if (!raw) return {};
  try { return JSON.parse(raw); } catch { throw new HttpError(400, 'JSON inválido.'); }
}

class HttpError extends Error {
  constructor(status, message) { super(message); this.status = status; }
}

function sessionUser(req, db) {
  const token = String(req.headers.authorization || '').replace(/^Bearer\s+/i, '');
  const session = sessions.get(token);
  if (!session || session.expiresAt < Date.now()) throw new HttpError(401, 'Sessão inválida ou expirada.');
  const user = db.users.find((item) => item.id === session.userId && item.active);
  if (!user) throw new HttpError(401, 'Usuário sem acesso.');
  return user;
}

function requireOperational(user) {
  if (![roles.ADMIN, roles.MOTORISTA].includes(user.role)) throw new HttpError(403, 'Seu perfil é somente de consulta.');
}

function requireAdmin(user) {
  if (user.role !== roles.ADMIN) throw new HttpError(403, 'Apenas administradores podem realizar esta ação.');
}

function findById(items, itemId, label) {
  const item = items.find((entry) => entry.id === itemId);
  if (!item) throw new HttpError(404, `${label} não encontrado.`);
  return item;
}

function changeDriver(db, driverId, status, { incrementTours = false, incrementHomePickups = false } = {}) {
  const driver = findById(db.drivers, driverId, 'Motorista');
  driver.status = status;
  if (incrementTours) driver.toursStarted += 1;
  if (incrementHomePickups) driver.homePickups += 1;
  driver.lastActivity = now();
  return driver;
}

function changeCart(db, cartId, status) {
  const cart = findById(db.carts, cartId, 'Carrinho');
  cart.status = status;
  return cart;
}

function logActivity(db, user, tour, previous, next, message) {
  db.activities.unshift({ id: id('act'), at: now(), userName: user.name, tourId: tour?.id, message, previous, next });
  db.activities = db.activities.slice(0, 250);
}

function stateLabel(state) {
  return {
    DISPONIVEL: 'Disponível no Prestige', EM_TOUR: 'Em tour', NA_CASA: 'Na Casa', AGUARDANDO_CASA: 'Aguardando na Casa',
    NA_GALERIA: 'Na Galeria', EM_APRESENTACAO: 'Em apresentação', AGUARDANDO_DESTINO: 'Aguardando destino',
    EM_DESTINO_FINAL: 'Em destino final', CONCLUIDO: 'Concluído'
  }[state] || state;
}

function setTourState(db, user, tour, next, message) {
  const previous = tour.status;
  tour.status = next;
  tour.updatedAt = now();
  logActivity(db, user, tour, previous, next, message);
}

function normalizeAllocations(db, allocations, people) {
  if (!Array.isArray(allocations) || !allocations.length) throw new HttpError(400, 'Selecione pelo menos um carrinho e um motorista.');
  const uniqueDrivers = new Set();
  const uniqueCarts = new Set();
  const normalized = allocations.map((entry) => {
    if (!entry.driverId || !entry.cartId) throw new HttpError(400, 'Cada alocação exige motorista e carrinho.');
    if (uniqueDrivers.has(entry.driverId) || uniqueCarts.has(entry.cartId)) throw new HttpError(400, 'Não repita motorista ou carrinho na mesma saída.');
    uniqueDrivers.add(entry.driverId); uniqueCarts.add(entry.cartId);
    const driver = findById(db.drivers, entry.driverId, 'Motorista');
    const cart = findById(db.carts, entry.cartId, 'Carrinho');
    if (driver.status !== driverStates.DISPONIVEL) throw new HttpError(400, `${driver.name} não está disponível.`);
    if (cart.status !== 'DISPONIVEL') throw new HttpError(400, `${cart.name} não está disponível.`);
    return { driverId: driver.id, cartId: cart.id, seats: Number(entry.seats || cart.capacity), arrived: false };
  });
  const capacity = normalized.reduce((total, entry) => total + entry.seats, 0);
  if (capacity < people) throw new HttpError(400, 'A capacidade dos carrinhos não atende todas as pessoas do grupo.');
  return normalized;
}

function applyAction(db, user, tour, action, payload) {
  requireOperational(user);
  const allocations = () => tour.allocations || [];

  if (action === 'start') {
    if (tour.status !== tourStates.DISPONIVEL) throw new HttpError(400, 'Apenas grupos disponíveis podem iniciar tour.');
    tour.allocations = normalizeAllocations(db, payload.allocations, tour.people);
    for (const allocation of allocations()) {
      changeDriver(db, allocation.driverId, driverStates.EM_TOUR, { incrementTours: true });
      changeCart(db, allocation.cartId, 'EM_USO');
    }
    tour.phase = 'Prestige Waves Bahia';
    setTourState(db, user, tour, tourStates.EM_TOUR, `${tour.groupName} iniciou tour no Prestige.`);
    return;
  }

  if (action === 'arrived-home') {
    if (tour.status !== tourStates.EM_TOUR) throw new HttpError(400, 'O grupo precisa estar em tour para chegar à Casa.');
    for (const allocation of allocations()) changeDriver(db, allocation.driverId, driverStates.CASA);
    tour.phase = 'Casa';
    setTourState(db, user, tour, tourStates.NA_CASA, `${tour.groupName} chegou à Casa.`);
    return;
  }

  if (action === 'return-prestige') {
    if (tour.status !== tourStates.NA_CASA) throw new HttpError(400, 'A ação é válida somente para grupos na Casa.');
    for (const allocation of allocations()) {
      changeDriver(db, allocation.driverId, driverStates.DISPONIVEL);
      changeCart(db, allocation.cartId, 'DISPONIVEL');
    }
    tour.allocations = [];
    tour.phase = 'Casa';
    setTourState(db, user, tour, tourStates.AGUARDANDO_CASA, `${tour.groupName} ficou aguardando transporte na Casa.`);
    return;
  }

  if (action === 'pickup-home') {
    if (tour.status !== tourStates.AGUARDANDO_CASA) throw new HttpError(400, 'O grupo não está aguardando na Casa.');
    tour.allocations = normalizeAllocations(db, payload.allocations, tour.people);
    for (const allocation of allocations()) {
      changeDriver(db, allocation.driverId, driverStates.EM_TOUR, { incrementHomePickups: true });
      changeCart(db, allocation.cartId, 'EM_USO');
    }
    tour.phase = 'Casa → Galeria';
    setTourState(db, user, tour, tourStates.EM_TOUR, `${tour.groupName} foi buscado na Casa para seguir à Galeria.`);
    return;
  }

  if (action === 'deliver-gallery') {
    if (![tourStates.EM_TOUR, tourStates.NA_CASA].includes(tour.status)) throw new HttpError(400, 'O grupo precisa estar em deslocamento para ser entregue na Galeria.');
    for (const allocation of allocations()) changeDriver(db, allocation.driverId, driverStates.GALERIA);
    tour.phase = 'Galeria';
    setTourState(db, user, tour, tourStates.NA_GALERIA, `${tour.groupName} foi entregue na Galeria.`);
    return;
  }

  if (action === 'presentation-started') {
    if (tour.status !== tourStates.NA_GALERIA) throw new HttpError(400, 'O grupo precisa estar na Galeria.');
    setTourState(db, user, tour, tourStates.EM_APRESENTACAO, `Apresentação iniciada para ${tour.groupName}.`);
    return;
  }

  if (action === 'presentation-finished') {
    if (![tourStates.NA_GALERIA, tourStates.EM_APRESENTACAO].includes(tour.status)) throw new HttpError(400, 'A apresentação ainda não está em andamento.');
    if (!payload.destinationId) throw new HttpError(400, 'Informe o destino final.');
    findById(db.destinations, payload.destinationId, 'Destino');
    for (const allocation of allocations()) {
      changeDriver(db, allocation.driverId, driverStates.DISPONIVEL);
      changeCart(db, allocation.cartId, 'DISPONIVEL');
    }
    tour.allocations = [];
    tour.destinationId = payload.destinationId;
    tour.phase = 'Galeria';
    setTourState(db, user, tour, tourStates.AGUARDANDO_DESTINO, `${tour.groupName} concluiu a apresentação e aguarda destino.`);
    return;
  }

  if (action === 'assign-destination') {
    if (tour.status !== tourStates.AGUARDANDO_DESTINO) throw new HttpError(400, 'O grupo não está aguardando destino.');
    tour.allocations = normalizeAllocations(db, payload.allocations, tour.people);
    for (const allocation of allocations()) {
      changeDriver(db, allocation.driverId, driverStates.DESTINO_FINAL);
      changeCart(db, allocation.cartId, 'EM_USO');
    }
    tour.phase = 'Destino final';
    setTourState(db, user, tour, tourStates.EM_DESTINO_FINAL, `${tour.groupName} saiu para o destino final.`);
    return;
  }

  if (action === 'complete-destination') {
    if (tour.status !== tourStates.EM_DESTINO_FINAL) throw new HttpError(400, 'O grupo ainda não está em destino final.');
    for (const allocation of allocations()) {
      changeDriver(db, allocation.driverId, driverStates.DISPONIVEL);
      changeCart(db, allocation.cartId, 'DISPONIVEL');
    }
    tour.phase = 'Concluído';
    setTourState(db, user, tour, tourStates.CONCLUIDO, `${tour.groupName} concluiu o destino final.`);
    return;
  }

  throw new HttpError(404, 'Ação operacional não encontrada.');
}

function isPathSafe(pathname) {
  const relative = normalize(pathname.replace(/^\/+/, ''));
  return !relative.startsWith('..') && !relative.includes(':');
}

const contentTypes = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8', '.svg': 'image/svg+xml', '.png': 'image/png', '.ico': 'image/x-icon' };

async function staticFile(res, pathname) {
  const wanted = pathname === '/' ? 'index.html' : pathname;
  if (!isPathSafe(wanted)) throw new HttpError(404, 'Arquivo não encontrado.');
  let filePath = join(distDir, wanted);
  try {
    await access(filePath);
  } catch {
    filePath = join(distDir, 'index.html');
  }
  const payload = await readFile(filePath);
  res.writeHead(200, { 'Content-Type': contentTypes[extname(filePath)] || 'application/octet-stream' });
  res.end(payload);
}

const server = createServer(async (req, res) => {
  try {
    const url = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
    const pathname = url.pathname;

    if (!pathname.startsWith('/api/')) return staticFile(res, pathname);
    const db = await database();

    if (pathname === '/api/auth/login' && req.method === 'POST') {
      const payload = await body(req);
      const user = db.users.find((entry) => entry.username.toLowerCase() === String(payload.username || '').trim().toLowerCase() && entry.active);
      if (!user || !(await passwordMatches(String(payload.password || ''), user.passwordHash))) throw new HttpError(401, 'Usuário ou senha inválidos.');
      const token = createHash('sha256').update(`${randomBytes(48).toString('hex')}:${user.id}`).digest('hex');
      sessions.set(token, { userId: user.id, expiresAt: Date.now() + 1000 * 60 * 60 * 12 });
      return json(res, 200, { token, user: sanitizeUser(user) });
    }

    if (pathname === '/api/auth/logout' && req.method === 'POST') {
      sessions.delete(String(req.headers.authorization || '').replace(/^Bearer\s+/i, ''));
      return json(res, 200, { ok: true });
    }

    const user = sessionUser(req, db);

    if (pathname === '/api/auth/me' && req.method === 'GET') return json(res, 200, { user: sanitizeUser(user) });
    if (pathname === '/api/bootstrap' && req.method === 'GET') return json(res, 200, { user: sanitizeUser(user), data: safeDatabase(db), states: tourStates, driverStates });

    if (pathname === '/api/users' && req.method === 'POST') {
      requireAdmin(user);
      const payload = await body(req);
      const username = String(payload.username || '').trim().toLowerCase();
      const name = String(payload.name || '').trim();
      if (!username || !name || !payload.password || !Object.values(roles).includes(payload.role)) throw new HttpError(400, 'Preencha nome, usuário, senha e perfil.');
      if (db.users.some((entry) => entry.username === username)) throw new HttpError(409, 'Esse usuário já existe.');
      const newUser = { id: id('user'), username, name, role: payload.role, active: true, passwordHash: await hashPassword(payload.password), createdAt: now() };
      db.users.push(newUser);
      logActivity(db, user, null, null, null, `Usuário ${name} criado com perfil ${payload.role}.`);
      await save(db);
      return json(res, 201, { user: sanitizeUser(newUser) });
    }

    if (pathname === '/api/tours' && req.method === 'POST') {
      requireOperational(user);
      const payload = await body(req);
      const groupName = String(payload.groupName || '').trim();
      const people = Number(payload.people);
      if (!groupName || !Number.isInteger(people) || people < 1 || people > 48) throw new HttpError(400, 'Informe o grupo e uma quantidade de pessoas entre 1 e 48.');
      findById(db.consultants, payload.consultantId, 'Consultor');
      const tour = { id: id('tour'), groupName, people, selfGuide: Boolean(payload.selfGuide), consultantId: payload.consultantId, status: tourStates.DISPONIVEL, phase: 'Prestige Praia do Forte', createdAt: now(), updatedAt: now(), allocations: [] };
      db.tours.unshift(tour);
      logActivity(db, user, tour, null, tourStates.DISPONIVEL, `${groupName} cadastrado como disponível no Prestige.`);
      await save(db);
      return json(res, 201, { tour });
    }

    const actionMatch = pathname.match(/^\/api\/tours\/([^/]+)\/action$/);
    if (actionMatch && req.method === 'POST') {
      const payload = await body(req);
      const tour = findById(db.tours, actionMatch[1], 'Tour');
      applyAction(db, user, tour, payload.action, payload);
      await save(db);
      return json(res, 200, { tour });
    }

    throw new HttpError(404, 'Rota não encontrada.');
  } catch (error) {
    const status = error instanceof HttpError ? error.status : 500;
    if (status === 500) console.error(error);
    return json(res, status, { error: error.message || 'Erro inesperado.' });
  }
});

server.listen(port, () => console.log(`Iberostar Tour API disponível em http://localhost:${port}`));

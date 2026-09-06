import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import { Clock3, LoaderCircle, MapPin, Navigation, Radio, ShieldCheck } from 'lucide-react';
import 'leaflet/dist/leaflet.css';


const LOCATION_SEND_INTERVAL_MS = 15000;
const LOCATION_REFRESH_INTERVAL_MS = 15000;
const DEFAULT_LOCATION_STALE_SECONDS = 90;
const DEFAULT_LOCATION_EXPIRES_SECONDS = 5 * 60;
const MAX_LOCAL_LOCATION_VISIBILITY_SECONDS = 5 * 60;
const WEAK_GPS_ACCURACY_METERS = 80;
const LOCATION_TIME_ZONE = 'America/Bahia';
const LOCATION_END_HOUR = 15;
const LOCATION_END_LABEL = '15:00';
const LOCATION_CUTOFF_MESSAGE = 'O compartilhamento de localização foi encerrado automaticamente às 15:00 (horário de Salvador).';
const MAP_TILE_URL = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
const MAP_ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';
const SALVADOR_CLOCK_FORMATTER = new Intl.DateTimeFormat('en-GB', {
  timeZone: LOCATION_TIME_ZONE,
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
  hourCycle: 'h23'
});
const SALVADOR_TIME_FORMATTER = new Intl.DateTimeFormat('pt-BR', {
  timeZone: LOCATION_TIME_ZONE,
  hour: '2-digit',
  minute: '2-digit',
  hourCycle: 'h23'
});


async function locationApi(token, path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {})
    }
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(payload.error || 'Não foi possível atualizar a localização.');
    error.status = response.status;
    throw error;
  }
  return payload;
}


function locationAge(value) {
  const timestamp = new Date(value).getTime();
  if (!Number.isFinite(timestamp)) return 'em horário desconhecido';
  const elapsed = Math.max(0, Date.now() - timestamp);
  if (elapsed < 10000) return 'agora';
  if (elapsed < 60000) return 'há menos de 1 min';
  const minutes = Math.max(1, Math.round(elapsed / 60000));
  return `há ${minutes} min`;
}


function salvadorSharingWindow(now = new Date()) {
  const values = Object.fromEntries(
    SALVADOR_CLOCK_FORMATTER.formatToParts(now)
      .filter((part) => part.type !== 'literal')
      .map((part) => [part.type, Number(part.value)])
  );
  const secondsToday = (values.hour * 60 * 60) + (values.minute * 60) + values.second;
  const cutoffSeconds = LOCATION_END_HOUR * 60 * 60;
  const open = secondsToday < cutoffSeconds;
  const secondsUntilBoundary = open ? cutoffSeconds - secondsToday : (24 * 60 * 60) - secondsToday;
  return {
    open,
    dateKey: `${values.year}-${String(values.month).padStart(2, '0')}-${String(values.day).padStart(2, '0')}`,
    millisecondsUntilBoundary: Math.max(250, (secondsUntilBoundary * 1000) - now.getMilliseconds() + 100)
  };
}


function useSalvadorSharingWindow() {
  const [windowState, setWindowState] = useState(() => salvadorSharingWindow());
  useEffect(() => {
    let timer = null;
    function updateWindow() {
      window.clearTimeout(timer);
      const nextWindow = salvadorSharingWindow();
      setWindowState(nextWindow);
      timer = window.setTimeout(updateWindow, nextWindow.millisecondsUntilBoundary);
    }
    function handleVisibility() {
      if (document.visibilityState === 'visible') updateWindow();
    }
    updateWindow();
    document.addEventListener('visibilitychange', handleVisibility);
    return () => {
      window.clearTimeout(timer);
      document.removeEventListener('visibilitychange', handleVisibility);
    };
  }, []);
  return windowState;
}


function sharingEndLabel(value) {
  if (value === null || value === undefined || value === '') return LOCATION_END_LABEL;
  if (typeof value === 'string') {
    const timeOnly = value.match(/^(\d{1,2}):(\d{2})/);
    if (timeOnly) return `${timeOnly[1].padStart(2, '0')}:${timeOnly[2]}`;
  }
  const timestamp = new Date(value).getTime();
  return Number.isFinite(timestamp) ? SALVADOR_TIME_FORMATTER.format(timestamp) : LOCATION_END_LABEL;
}


function locationTestModeMetadata(source) {
  const settings = source?.operationSettings && typeof source.operationSettings === 'object' ? source.operationSettings : {};
  const active = typeof source?.locationTestModeActive === 'boolean'
    ? source.locationTestModeActive
    : settings.locationTestModeActive === true;
  const endsAt = source?.locationTestModeEndsAt || settings.locationTestModeEndsAt || null;
  const driverId = source?.locationTestDriverId || settings.locationTestDriverId || null;
  const driverName = source?.locationTestDriverName || settings.locationTestDriverName || null;
  return { active, endsAt, driverId: driverId ? String(driverId) : null, driverName };
}


function locationTestModeEndTimestamp(value, now = new Date()) {
  if (value === null || value === undefined || value === '') return NaN;
  const timestamp = new Date(value).getTime();
  if (Number.isFinite(timestamp)) return timestamp;
  if (typeof value !== 'string') return NaN;
  const timeOnly = value.match(/^(\d{1,2}):(\d{2})(?::(\d{2}))?$/);
  if (!timeOnly) return NaN;
  const targetSeconds = (Number(timeOnly[1]) * 60 * 60) + (Number(timeOnly[2]) * 60) + Number(timeOnly[3] || 0);
  if (targetSeconds < 0 || targetSeconds >= 24 * 60 * 60) return NaN;
  const values = Object.fromEntries(
    SALVADOR_CLOCK_FORMATTER.formatToParts(now)
      .filter((part) => part.type !== 'literal')
      .map((part) => [part.type, Number(part.value)])
  );
  const currentSeconds = (values.hour * 60 * 60) + (values.minute * 60) + values.second;
  return now.getTime() + ((targetSeconds - currentSeconds) * 1000) - now.getMilliseconds();
}


function useLocationTestMode(source) {
  const metadata = locationTestModeMetadata(source);
  const [now, setNow] = useState(Date.now);
  const endsAtTimestamp = locationTestModeEndTimestamp(metadata.endsAt);
  useEffect(() => {
    let timer = null;
    function update() {
      window.clearTimeout(timer);
      const currentTime = Date.now();
      setNow(currentTime);
      const deadline = locationTestModeEndTimestamp(metadata.endsAt, new Date(currentTime));
      if (metadata.active && Number.isFinite(deadline) && deadline > currentTime) {
        timer = window.setTimeout(update, Math.max(50, deadline - currentTime + 25));
      }
    }
    function handleVisibility() {
      if (document.visibilityState === 'visible') update();
    }
    update();
    document.addEventListener('visibilitychange', handleVisibility);
    return () => {
      window.clearTimeout(timer);
      document.removeEventListener('visibilitychange', handleVisibility);
    };
  }, [metadata.active, metadata.endsAt]);
  const deadlineIsValid = Number.isFinite(endsAtTimestamp);
  return {
    active: metadata.active && deadlineIsValid && now < endsAtTimestamp,
    ended: metadata.active && (!deadlineIsValid || now >= endsAtTimestamp),
    endsAt: metadata.endsAt,
    endLabel: sharingEndLabel(metadata.endsAt),
    driverId: metadata.driverId,
    driverName: metadata.driverName
  };
}


function locationTestModeAppliesToDriver(testMode, driverId) {
  return Boolean(testMode.active && testMode.driverId && driverId && String(testMode.driverId) === String(driverId));
}


function LocationTestModeNotice({ testMode, showDriverName = false }) {
  if (!testMode.active) return null;
  const namedDriver = showDriverName && testMode.driverName ? String(testMode.driverName) : '';
  return <div className="location-test-mode-notice" role="status"><Clock3 size={17} /><div><strong>{namedDriver ? `Teste de localização ativo para ${namedDriver}` : 'Modo de teste de localização ativo'}</strong><span>{namedDriver ? `Após as 15:00, somente ${namedDriver} poderá compartilhar, até ${testMode.endLabel} (Salvador).` : `O limite das 15:00 está suspenso somente até ${testMode.endLabel} (Salvador).`}</span></div></div>;
}


function normalizedLocation(value) {
  if (!value || typeof value !== 'object') return null;
  if (value.latitude === null || value.latitude === '' || value.longitude === null || value.longitude === '') return null;
  const latitude = Number(value.latitude);
  const longitude = Number(value.longitude);
  if (!Number.isFinite(latitude) || latitude < -90 || latitude > 90) return null;
  if (!Number.isFinite(longitude) || longitude < -180 || longitude > 180) return null;
  const accuracyValue = value.accuracy === null || value.accuracy === '' ? NaN : Number(value.accuracy);
  return {
    driverId: String(value.driverId || ''),
    driverName: String(value.driverName || 'Motorista'),
    kind: value.kind === 'hostess' ? 'hostess' : 'driver',
    latitude,
    longitude,
    accuracy: Number.isFinite(accuracyValue) && accuracyValue >= 0 ? accuracyValue : null,
    updatedAt: value.updatedAt,
    receivedAt: Date.now(),
    stale: Boolean(value.stale)
  };
}


function normalizedLocations(values) {
  const result = [];
  const seenDriverIds = new Set();
  (Array.isArray(values) ? values : []).forEach((value) => {
    const location = normalizedLocation(value);
    if (!location || !location.driverId || seenDriverIds.has(location.driverId)) return;
    seenDriverIds.add(location.driverId);
    result.push(location);
  });
  return result;
}


function boundedLocationSeconds(value, fallback) {
  if (value === null || value === undefined || value === '') return fallback;
  const seconds = Number(value);
  return Number.isFinite(seconds) && seconds >= 0 ? Math.min(seconds, MAX_LOCAL_LOCATION_VISIBILITY_SECONDS) : fallback;
}


function locationAgePolicy(payload) {
  const expiresAfterSeconds = boundedLocationSeconds(
    payload?.expiresAfterSeconds ?? payload?.ttlSeconds,
    DEFAULT_LOCATION_EXPIRES_SECONDS
  );
  const staleAfterSeconds = Math.min(
    boundedLocationSeconds(payload?.staleAfterSeconds, DEFAULT_LOCATION_STALE_SECONDS),
    expiresAfterSeconds
  );
  return { staleAfterSeconds, expiresAfterSeconds };
}


function locationFreshDeadline(location, visibilitySeconds) {
  const updatedAt = new Date(location?.updatedAt).getTime();
  const receivedAt = Number(location?.receivedAt);
  if (!Number.isFinite(updatedAt) || !Number.isFinite(receivedAt)) return NaN;
  const lifetime = Math.max(0, visibilitySeconds) * 1000;
  // receivedAt is an additional fail-safe if a malformed/future updatedAt is
  // returned or the device clock changes after the response.
  return Math.min(updatedAt + lifetime, receivedAt + lifetime);
}


function localLocationAgeState(location, policy, now) {
  if (!location) return 'expired';
  const expiresAt = locationFreshDeadline(location, policy.expiresAfterSeconds);
  if (!Number.isFinite(expiresAt) || now >= expiresAt) return 'expired';
  const staleAt = locationFreshDeadline(location, policy.staleAfterSeconds);
  if (location.stale || !Number.isFinite(staleAt) || now >= staleAt) return 'stale';
  return 'fresh';
}


function useLocationAgeClock(locations, thresholdsSeconds) {
  const [now, setNow] = useState(Date.now);
  const timestampsKey = (locations || []).map((location) => `${location.driverId}:${location.updatedAt}:${location.receivedAt}`).join('|');
  const thresholdsKey = (thresholdsSeconds || []).join('|');
  useEffect(() => {
    let timer = null;
    function schedule() {
      window.clearTimeout(timer);
      const currentTime = Date.now();
      setNow(currentTime);
      const futureDeadlines = (locations || [])
        .flatMap((location) => (thresholdsSeconds || []).map((seconds) => locationFreshDeadline(location, seconds)))
        .filter((deadline) => Number.isFinite(deadline) && deadline > currentTime);
      if (futureDeadlines.length) {
        const nextDeadline = Math.min(...futureDeadlines);
        timer = window.setTimeout(schedule, Math.max(50, nextDeadline - currentTime + 25));
      }
    }
    function handleVisibility() {
      if (document.visibilityState === 'visible') schedule();
    }
    schedule();
    document.addEventListener('visibilitychange', handleVisibility);
    return () => {
      window.clearTimeout(timer);
      document.removeEventListener('visibilitychange', handleVisibility);
    };
  }, [timestampsKey, thresholdsKey]);
  return now;
}


function geolocationErrorMessage(error) {
  if (error?.code === 1) return 'A localização foi bloqueada. Libere a permissão deste site nas configurações do navegador.';
  if (error?.code === 2) return 'O celular não conseguiu encontrar sua posição. Verifique se o GPS está ativado.';
  if (error?.code === 3) return 'O GPS demorou para responder. Tente novamente em um local com melhor sinal.';
  return 'Não foi possível obter sua localização neste aparelho.';
}


export function getCurrentBrowserLocation() {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error('Este aparelho não oferece localização pelo navegador.'));
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (position) => resolve({
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
        accuracy: Number.isFinite(position.coords.accuracy) ? position.coords.accuracy : null
      }),
      (error) => reject(new Error(geolocationErrorMessage(error))),
      { enableHighAccuracy: true, maximumAge: 10000, timeout: 20000 }
    );
  });
}


export function DriverLocationSharingCard({ data, user, token, notify }) {
  const attendance = (data.attendance || []).find((item) => item.userId === user.id);
  const sharingWindow = useSalvadorSharingWindow();
  const locationTestMode = useLocationTestMode(data);
  const attendanceForToday = attendance && (!attendance.operationDate || attendance.operationDate === sharingWindow.dateKey) ? attendance : null;
  const linkedDriver = (data.drivers || []).find((item) => String(item.id) === String(user.driverId || ''));
  const locationTestModeForDriver = {
    ...locationTestMode,
    active: locationTestModeAppliesToDriver(locationTestMode, user.driverId)
  };
  const driverCannotShare = Boolean(linkedDriver && (linkedDriver.active === false || ['FOLGA', 'ATESTADO'].includes(linkedDriver.status)));
  const watchIdRef = useRef(null);
  const sharingIdRef = useRef('');
  const lastAttemptAtRef = useRef(0);
  const inFlightGenerationRef = useRef(null);
  const startRequestRef = useRef(null);
  const generationRef = useRef(0);
  const mountedRef = useRef(true);
  const locationTestModeRef = useRef(locationTestModeForDriver);
  locationTestModeRef.current = locationTestModeForDriver;
  const [state, setState] = useState('off');
  const [detail, setDetail] = useState('');
  const [lastLocation, setLastLocation] = useState(null);

  function locationSharingWindowIsOpen() {
    return locationTestModeRef.current.active || salvadorSharingWindow().open;
  }

  function locationSharingClosedMessage() {
    const currentTestMode = locationTestModeRef.current;
    if (currentTestMode.ended && currentTestMode.driverId && String(currentTestMode.driverId) === String(user.driverId || '')) {
      return `O modo de teste terminou às ${currentTestMode.endLabel} (horário de Salvador) e o compartilhamento foi encerrado.`;
    }
    return LOCATION_CUTOFF_MESSAGE;
  }

  function clearWatcher() {
    if (watchIdRef.current !== null && navigator.geolocation) {
      navigator.geolocation.clearWatch(watchIdRef.current);
    }
    watchIdRef.current = null;
  }

  function isCurrentGeneration(generation) {
    return mountedRef.current && generationRef.current === generation;
  }

  async function transmitPosition(position, force = false, generation = generationRef.current) {
    const sharingId = sharingIdRef.current;
    const attendanceId = attendanceForToday?.id;
    if (!sharingId || !attendanceId || !isCurrentGeneration(generation)) return;
    if (!locationSharingWindowIsOpen()) {
      const closedMessage = locationSharingClosedMessage();
      void stopSharing({
        quiet: true,
        finalState: 'cutoff',
        finalDetail: closedMessage,
        completionMessage: closedMessage
      });
      return;
    }
    if (inFlightGenerationRef.current === generation) return;
    const now = Date.now();
    if (!force && now - lastAttemptAtRef.current < LOCATION_SEND_INTERVAL_MS) return;
    lastAttemptAtRef.current = now;
    inFlightGenerationRef.current = generation;
    try {
      const result = await locationApi(token, '/api/drivers/me/location', {
        method: 'PUT',
        body: JSON.stringify({
          attendanceId,
          sharingId,
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          accuracy: position.coords.accuracy
        })
      });
      if (!isCurrentGeneration(generation) || sharingIdRef.current !== sharingId) return;
      setLastLocation(result.location);
      setState(result.location?.accuracy > WEAK_GPS_ACCURACY_METERS ? 'weak' : 'sharing');
      setDetail(result.location?.accuracy > WEAK_GPS_ACCURACY_METERS ? 'Sinal de GPS fraco; a posição é apenas aproximada.' : 'Posição atualizada para a equipe autorizada.');
    } catch (error) {
      if (!isCurrentGeneration(generation)) return;
      if ([401, 403, 409].includes(error.status)) {
        clearWatcher();
        sharingIdRef.current = '';
        setState('error');
        setDetail(error.message);
        notify(error.message, 'error');
      } else {
        // A perda momentânea de rede não deve desligar silenciosamente o GPS.
        // O próximo evento do watchPosition tentará enviar a posição novamente.
        setState('weak');
        setDetail('Sem conexão para atualizar agora. A última posição ficará marcada como desatualizada até o envio voltar a funcionar.');
      }
    } finally {
      if (inFlightGenerationRef.current === generation) inFlightGenerationRef.current = null;
    }
  }

  function handleWatchError(error, generation) {
    if (!isCurrentGeneration(generation)) return;
    const message = geolocationErrorMessage(error);
    if (error?.code === 1) {
      clearWatcher();
      sharingIdRef.current = '';
      generationRef.current += 1;
      setState('blocked');
      locationApi(token, '/api/drivers/me/location-sharing', { method: 'DELETE' }).catch(() => undefined);
    } else {
      setState('weak');
    }
    setDetail(message);
  }

  function beginWatch(firstPosition, generation) {
    void transmitPosition(firstPosition, true, generation);
    const watchId = navigator.geolocation.watchPosition(
      (position) => void transmitPosition(position, false, generation),
      (error) => handleWatchError(error, generation),
      { enableHighAccuracy: true, maximumAge: 5000, timeout: 15000 }
    );
    if (isCurrentGeneration(generation)) watchIdRef.current = watchId;
    else navigator.geolocation.clearWatch(watchId);
  }

  async function startSharing() {
    if (!attendanceForToday?.id) {
      notify('Faça o check-in antes de compartilhar sua localização.', 'error');
      return;
    }
    if (!locationSharingWindowIsOpen()) {
      setState('cutoff');
      const closedMessage = locationSharingClosedMessage();
      setDetail(closedMessage);
      notify(closedMessage, 'error');
      return;
    }
    if (!user.driverId) {
      notify('Seu usuário não está vinculado a um motorista.', 'error');
      return;
    }
    if (driverCannotShare) {
      notify('Sua situação está como folga, atestado ou cadastro inativo.', 'error');
      return;
    }
    if (!('geolocation' in navigator)) {
      setState('error');
      setDetail('Este navegador não oferece localização.');
      return;
    }
    if (watchIdRef.current !== null || ['starting', 'stopping'].includes(state)) return;
    const generation = generationRef.current + 1;
    generationRef.current = generation;
    lastAttemptAtRef.current = 0;
    setState('starting');
    setDetail('Aguardando autorização e sinal do GPS…');
    navigator.geolocation.getCurrentPosition(async (position) => {
      if (!isCurrentGeneration(generation)) return;
      if (!locationSharingWindowIsOpen()) {
        const closedMessage = locationSharingClosedMessage();
        void stopSharing({
          quiet: true,
          finalState: 'cutoff',
          finalDetail: closedMessage,
          completionMessage: closedMessage
        });
        return;
      }
      try {
        const request = locationApi(token, '/api/drivers/me/location-sharing', {
          method: 'POST',
          body: JSON.stringify({ attendanceId: attendanceForToday.id })
        });
        startRequestRef.current = { generation, request };
        const result = await request;
        if (!isCurrentGeneration(generation)) return;
        if (!result.sharingId) throw new Error('O servidor não iniciou o compartilhamento de localização.');
        sharingIdRef.current = result.sharingId;
        if (!locationSharingWindowIsOpen()) {
          const closedMessage = locationSharingClosedMessage();
          void stopSharing({
            quiet: true,
            finalState: 'cutoff',
            finalDetail: closedMessage,
            completionMessage: closedMessage
          });
          return;
        }
        beginWatch(position, generation);
      } catch (error) {
        if (!isCurrentGeneration(generation)) return;
        setState('error');
        setDetail(error.message);
        notify(error.message, 'error');
      } finally {
        if (startRequestRef.current?.generation === generation) startRequestRef.current = null;
      }
    }, (error) => {
      if (!isCurrentGeneration(generation)) return;
      setState(error?.code === 1 ? 'blocked' : 'error');
      setDetail(geolocationErrorMessage(error));
    }, { enableHighAccuracy: true, maximumAge: 0, timeout: 15000 });
  }

  async function stopSharing({ quiet = false, finalState = 'off', finalDetail = '', completionMessage = '' } = {}) {
    const stopGeneration = generationRef.current + 1;
    generationRef.current = stopGeneration;
    const pendingStart = startRequestRef.current?.request;
    clearWatcher();
    sharingIdRef.current = '';
    lastAttemptAtRef.current = 0;
    inFlightGenerationRef.current = null;
    const showProgress = !quiet || finalState === 'cutoff';
    setState(showProgress ? 'stopping' : finalState);
    setDetail(showProgress ? (finalState === 'cutoff' ? 'Encerrando automaticamente o compartilhamento de localização…' : 'Encerrando a sessão de localização…') : finalDetail);
    setLastLocation(null);
    let stopError = null;
    try {
      await locationApi(token, '/api/drivers/me/location-sharing', { method: 'DELETE' });
    } catch (error) {
      stopError = error;
    }
    // Se o usuário tocou em "Parar" enquanto o POST inicial ainda estava em
    // trânsito, apague novamente após ele terminar. Uma nova ativação invalida
    // esta limpeza para que a sessão nova não seja removida por engano.
    if (pendingStart) {
      await pendingStart.catch(() => undefined);
      if (isCurrentGeneration(stopGeneration)) {
        try {
          await locationApi(token, '/api/drivers/me/location-sharing', { method: 'DELETE' });
          stopError = null;
        } catch (error) {
          stopError = error;
        }
      }
    }
    if (!isCurrentGeneration(stopGeneration)) return;
    setState(finalState);
    setDetail(finalDetail);
    if (completionMessage) notify(completionMessage, 'success');
    if (quiet) return;
    if (stopError) {
      notify(`${stopError.message} A posição deixará de aparecer automaticamente quando ficar desatualizada.`, 'error');
    } else {
      notify('Compartilhamento de localização encerrado.', 'success');
    }
  }

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      generationRef.current += 1;
      clearWatcher();
    };
  }, []);
  useEffect(() => {
    if (!attendanceForToday && (watchIdRef.current !== null || sharingIdRef.current || state === 'starting')) void stopSharing({ quiet: true });
  }, [attendanceForToday?.id]);
  useEffect(() => {
    if (locationTestModeForDriver.active || (sharingWindow.open && salvadorSharingWindow().open)) {
      if (state === 'cutoff') {
        setState('off');
        setDetail('');
      }
      return;
    }
    if (['starting', 'sharing', 'weak'].includes(state) || watchIdRef.current !== null || sharingIdRef.current) {
      const closedMessage = locationSharingClosedMessage();
      void stopSharing({
        quiet: true,
        finalState: 'cutoff',
        finalDetail: closedMessage,
        completionMessage: closedMessage
      });
      return;
    }
    if (state !== 'stopping' && state !== 'cutoff') {
      setState('cutoff');
      setDetail(locationSharingClosedMessage());
    }
  }, [sharingWindow.open, locationTestModeForDriver.active, state]);

  if (!attendanceForToday) return null;
  const active = ['starting', 'sharing', 'weak', 'stopping'].includes(state);
  const cutoffReached = !locationTestModeForDriver.active && (!sharingWindow.open || state === 'cutoff');
  const defaultDetail = locationTestModeForDriver.active
    ? `Você foi selecionado para este teste e pode compartilhar até ${locationTestModeForDriver.endLabel} (horário de Salvador). Fora do modo de teste, o limite normal é 15:00.`
    : 'Após o check-in, você pode compartilhar sua posição até as 15:00 (horário de Salvador). A atualização funciona enquanto este painel estiver aberto.';
  return <section className={`location-sharing-card location-sharing-${state}`}>
    <div className="location-sharing-icon">{active ? <Navigation size={24} /> : <MapPin size={24} />}</div>
    <div className="location-sharing-copy">
      <span>LOCALIZAÇÃO DURANTE O EXPEDIENTE</span>
      <h2>{state === 'starting' ? 'Obtendo sua posição…' : state === 'stopping' ? 'Encerrando compartilhamento…' : cutoffReached ? 'Período de localização encerrado' : state === 'sharing' ? 'Localização compartilhada' : state === 'weak' ? 'Compartilhando com sinal limitado' : state === 'blocked' ? 'Localização bloqueada' : 'Compartilhamento desativado'}</h2>
      <LocationTestModeNotice testMode={locationTestModeForDriver} showDriverName />
      <p aria-live="polite">{detail || defaultDetail}</p>
      {lastLocation && <small><Radio size={13} /> Atualizado {locationAge(lastLocation.updatedAt)}{Number.isFinite(lastLocation.accuracy) ? ` · precisão aproximada de ${Math.round(lastLocation.accuracy)} m` : ''}</small>}
    </div>
    {active ? <button className="button button-secondary" type="button" onClick={() => void stopSharing()} disabled={state === 'stopping'}>{state === 'stopping' && <LoaderCircle className="spin" size={17} />} {state === 'stopping' ? 'Encerrando…' : 'Parar compartilhamento'}</button> : <button className="button button-primary" type="button" onClick={startSharing} disabled={driverCannotShare || cutoffReached}><Navigation size={17} /> {cutoffReached ? 'Período encerrado' : 'Compartilhar minha localização'}</button>}
  </section>;
}


function DriverMapCanvas({ locations, fitRequest, ariaLabel = 'Mapa interativo com a última localização compartilhada pelos motoristas' }) {
  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const locationLayerRef = useRef(null);
  const fittedRef = useRef(false);
  const fittedRequestRef = useRef(fitRequest);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return undefined;
    const first = locations[0];
    if (!first) return undefined;
    const map = L.map(containerRef.current, {
      zoomControl: true,
      attributionControl: true,
      dragging: !L.Browser.mobile,
      scrollWheelZoom: false
    }).setView([first.latitude, first.longitude], 16);
    L.tileLayer(MAP_TILE_URL, { attribution: MAP_ATTRIBUTION, maxZoom: 19, updateWhenIdle: true }).addTo(map);
    locationLayerRef.current = L.layerGroup().addTo(map);
    mapRef.current = map;
    const resizeMap = () => map.invalidateSize({ pan: false });
    const resizeTimer = window.setTimeout(resizeMap, 0);
    const resizeObserver = 'ResizeObserver' in window ? new ResizeObserver(resizeMap) : null;
    resizeObserver?.observe(containerRef.current);
    return () => {
      window.clearTimeout(resizeTimer);
      resizeObserver?.disconnect();
      map.remove();
      mapRef.current = null;
      locationLayerRef.current = null;
      fittedRef.current = false;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    const layer = locationLayerRef.current;
    if (!map || !layer) return;
    layer.clearLayers();
    const markers = [];
    const hostessLocation = locations.find((location) => location.kind === 'hostess');
    const driverLocation = locations.find((location) => location.kind === 'driver');
    if (hostessLocation && driverLocation) {
      L.polyline(
        [[hostessLocation.latitude, hostessLocation.longitude], [driverLocation.latitude, driverLocation.longitude]],
        { color: '#4866c8', opacity: .7, weight: 3, dashArray: '7 8' }
      ).addTo(layer);
    }
    locations.forEach((location) => {
      const point = [location.latitude, location.longitude];
      const color = location.stale ? '#d17a18' : location.kind === 'hostess' ? '#5367c7' : '#087f72';
      if (Number.isFinite(location.accuracy)) {
        L.circle(point, { radius: Math.min(location.accuracy, 500), color, fillColor: color, fillOpacity: .06, weight: 1 }).addTo(layer);
      }
      const marker = L.circleMarker(point, { radius: 9, color: '#fff', fillColor: color, fillOpacity: 1, weight: 3 }).addTo(layer);
      const tooltip = document.createElement('span');
      const markerLabel = `${location.driverName} · ${location.stale ? 'posição desatualizada' : 'posição recente'} · atualizada ${locationAge(location.updatedAt)}`;
      tooltip.textContent = markerLabel;
      marker.bindTooltip(tooltip, { direction: 'top', offset: [0, -8] });
      const markerElement = marker.getElement();
      if (markerElement) {
        markerElement.setAttribute('tabindex', '0');
        markerElement.setAttribute('role', 'button');
        markerElement.setAttribute('aria-label', markerLabel);
        markerElement.addEventListener('focus', () => marker.openTooltip());
        markerElement.addEventListener('blur', () => marker.closeTooltip());
        markerElement.addEventListener('keydown', (event) => {
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            marker.toggleTooltip();
          }
        });
      }
      markers.push(marker);
    });
    const requestedFit = fittedRequestRef.current !== fitRequest;
    if ((!fittedRef.current || requestedFit) && markers.length) {
      const bounds = L.featureGroup(markers).getBounds();
      if (markers.length === 1) map.setView(bounds.getCenter(), 17);
      else map.fitBounds(bounds, { padding: [35, 35], maxZoom: 17 });
      fittedRef.current = true;
      fittedRequestRef.current = fitRequest;
    }
  }, [locations, fitRequest]);

  return <div ref={containerRef} className="driver-map-canvas" role="region" aria-label={ariaLabel} />;
}


export function DriverLocationMapPanel({ token }) {
  const localSharingWindow = useSalvadorSharingWindow();
  const [locations, setLocations] = useState([]);
  const [agePolicy, setAgePolicy] = useState(() => locationAgePolicy(null));
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [reloadKey, setReloadKey] = useState(0);
  const [fitRequest, setFitRequest] = useState(0);
  const [serverSharingWindow, setServerSharingWindow] = useState({
    open: null,
    endsAt: null,
    locationTestModeActive: false,
    locationTestModeEndsAt: null,
    locationTestDriverId: null,
    locationTestDriverName: null
  });
  const locationTestMode = useLocationTestMode(serverSharingWindow);

  useEffect(() => {
    let active = true;
    let requestController = null;
    async function loadLocations() {
      if (requestController) return;
      requestController = new AbortController();
      try {
        const payload = await locationApi(token, '/api/driver-locations', { signal: requestController.signal });
        if (!active) return;
        const serverWindowOpen = typeof payload.sharingWindowOpen === 'boolean' ? payload.sharingWindowOpen : null;
        setServerSharingWindow({
          open: serverWindowOpen,
          endsAt: payload.sharingEndsAt || null,
          locationTestModeActive: payload.locationTestModeActive === true,
          locationTestModeEndsAt: payload.locationTestModeEndsAt || null,
          locationTestDriverId: payload.locationTestDriverId || null,
          locationTestDriverName: payload.locationTestDriverName || null
        });
        setAgePolicy(locationAgePolicy(payload));
        setLocations(serverWindowOpen === false ? [] : normalizedLocations(payload.locations));
        setError('');
      } catch (requestError) {
        if (active && requestError.name !== 'AbortError') {
          // Revogação de sessão/permissão retira tudo imediatamente. Em uma
          // falha transitória a Hostess ainda vê somente um ponto dentro do
          // prazo local; o timer abaixo o remove mesmo sem novas respostas.
          if ([401, 403].includes(requestError.status)) setLocations([]);
          setError(requestError.message);
        }
      } finally {
        requestController = null;
        if (active) setLoading(false);
      }
    }
    loadLocations();
    const timer = window.setInterval(() => {
      if (document.visibilityState === 'visible') loadLocations();
    }, LOCATION_REFRESH_INTERVAL_MS);
    const handleVisibility = () => { if (document.visibilityState === 'visible') loadLocations(); };
    document.addEventListener('visibilitychange', handleVisibility);
    return () => {
      active = false;
      requestController?.abort();
      window.clearInterval(timer);
      document.removeEventListener('visibilitychange', handleVisibility);
    };
  }, [token, reloadKey]);

  const ageNow = useLocationAgeClock(locations, [agePolicy.staleAfterSeconds, agePolicy.expiresAfterSeconds]);
  // O servidor continua autoritativo para encerrar antes, e o limite local
  // impede que uma última resposta das 14h permaneça no mapa após as 15h.
  const hostessLocationTestActive = Boolean(locationTestMode.active && locationTestMode.driverId);
  const sharingPeriodClosed = (!hostessLocationTestActive && !localSharingWindow.open) || serverSharingWindow.open === false;
  const scopedLocations = !localSharingWindow.open && hostessLocationTestActive
    ? locations.filter((location) => String(location.driverId) === String(locationTestMode.driverId))
    : locations;
  const visibleLocations = sharingPeriodClosed ? [] : scopedLocations.map((location) => {
    const ageState = localLocationAgeState(location, agePolicy, ageNow);
    return ageState === 'expired' ? null : { ...location, stale: ageState === 'stale' };
  }).filter(Boolean);
  const freshCount = visibleLocations.filter((location) => !location.stale).length;
  const endLabel = sharingEndLabel(serverSharingWindow.endsAt);
  return <section className="panel driver-map-panel">
    <div className="panel-heading"><div><h2>Localização dos motoristas</h2><p>{sharingPeriodClosed ? `Período de localização encerrado às ${endLabel} (horário de Salvador).` : 'Última posição compartilhada durante o expediente. Pontos antigos desaparecem automaticamente.'}</p></div><div className="driver-map-heading-actions"><span className="location-map-count" aria-live="polite">{sharingPeriodClosed ? <ShieldCheck size={14} /> : <Radio size={14} />} {sharingPeriodClosed ? `Encerrado às ${endLabel}` : `${freshCount} ao vivo`}</span>{visibleLocations.length > 0 && <button className="text-button" type="button" onClick={() => setFitRequest((value) => value + 1)}><Navigation size={14} /> Centralizar</button>}</div></div>
    <LocationTestModeNotice testMode={{ ...locationTestMode, active: hostessLocationTestActive }} showDriverName />
    {error && <div className="driver-map-error" role="alert"><span>{error}</span><button className="text-button" type="button" onClick={() => { setLoading(!visibleLocations.length); setReloadKey((value) => value + 1); }}>Tentar novamente</button></div>}
    {!error && sharingPeriodClosed ? <div className="driver-map-empty"><ShieldCheck size={26} /><div><strong>Período de localização encerrado</strong><span>O compartilhamento dos motoristas terminou às {endLabel} (horário de Salvador).</span></div></div> : loading ? <div className="driver-map-empty" role="status"><LoaderCircle className="spin" size={25} /> Carregando localizações…</div> : !error && !visibleLocations.length ? <div className="driver-map-empty"><MapPin size={26} /><div><strong>Nenhum motorista compartilhando agora</strong><span>{hostessLocationTestActive ? `Para o teste após as 15:00, ${locationTestMode.driverName || 'o motorista selecionado'} precisa fazer check-in e ativar a localização no próprio celular.` : 'Após o check-in, o motorista precisa ativar a localização no próprio celular até as 15:00.'}</span></div></div> : visibleLocations.length ? <div className="driver-map-layout"><div className="driver-map-frame"><DriverMapCanvas locations={visibleLocations} fitRequest={fitRequest} /></div><div className="location-driver-list" aria-label="Motoristas exibidos no mapa">{visibleLocations.map((location) => <article key={location.driverId} className={location.stale ? 'location-stale' : ''}><span className="location-driver-dot" aria-hidden="true" /><div><strong>{location.driverName}</strong><small>{location.stale ? 'Sinal desatualizado' : 'Localização recente'} · {locationAge(location.updatedAt)}{Number.isFinite(location.accuracy) ? ` · ±${Math.round(location.accuracy)} m` : ''}</small></div></article>)}</div></div> : null}
    <div className="driver-map-privacy"><ShieldCheck size={15} /> Neste sistema, as coordenadas são entregues somente à Hostess autenticada. Consultores recebem apenas o motorista ligado ao próprio pedido; o fundo cartográfico é fornecido pelo OpenStreetMap.</div>
  </section>;
}


function distanceBetweenLocations(first, second) {
  if (!first || !second) return NaN;
  const radians = (value) => value * Math.PI / 180;
  const latitudeDelta = radians(second.latitude - first.latitude);
  const longitudeDelta = radians(second.longitude - first.longitude);
  const firstLatitude = radians(first.latitude);
  const secondLatitude = radians(second.latitude);
  const haversine = Math.sin(latitudeDelta / 2) ** 2
    + Math.cos(firstLatitude) * Math.cos(secondLatitude) * Math.sin(longitudeDelta / 2) ** 2;
  return 6371000 * 2 * Math.atan2(Math.sqrt(haversine), Math.sqrt(1 - haversine));
}


function distanceLabel(distance) {
  if (!Number.isFinite(distance)) return '';
  if (distance < 1000) return `${Math.max(0, Math.round(distance / 10) * 10)} m`;
  return `${(distance / 1000).toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })} km`;
}


function approachLocations(payload) {
  const request = payload?.request || {};
  const hostess = payload?.hostessLocation ? normalizedLocation({
    ...payload.hostessLocation,
    driverId: `hostess-${request.id || 'solicitante'}`,
    driverName: `Hostess ${payload.hostessLocation.hostessName || request.requestedByName || ''}`.trim(),
    kind: 'hostess'
  }) : null;
  const driver = payload?.driverLocation ? normalizedLocation({
    ...payload.driverLocation,
    driverId: `driver-${request.id || 'apoio'}`,
    driverName: payload.driverLocation.driverName || request.assignedDriverName || 'Motorista em apoio',
    kind: 'driver'
  }) : null;
  return { hostess, driver };
}


export function HostessApproachLocationPanel({ requestId, token, shareHostessLocation = false }) {
  const localSharingWindow = useSalvadorSharingWindow();
  const [request, setRequest] = useState(null);
  const [hostessLocation, setHostessLocation] = useState(null);
  const [driverLocation, setDriverLocation] = useState(null);
  const [agePolicy, setAgePolicy] = useState(() => locationAgePolicy(null));
  const [serverSharingWindow, setServerSharingWindow] = useState({ open: null, endsAt: null, locationTestModeActive: false, locationTestModeEndsAt: null });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [sharingError, setSharingError] = useState('');
  const [reloadKey, setReloadKey] = useState(0);
  const [fitRequest, setFitRequest] = useState(0);
  const previousDistanceRef = useRef(NaN);
  const [movementLabel, setMovementLabel] = useState('Acompanhando aproximação');
  const locationTestMode = useLocationTestMode(serverSharingWindow);

  useEffect(() => {
    let active = true;
    let requestController = null;
    async function loadApproach() {
      if (requestController) return;
      requestController = new AbortController();
      try {
        const payload = await locationApi(token, `/api/hostess-requests/${requestId}/approach`, { signal: requestController.signal });
        if (!active) return;
        const points = approachLocations(payload);
        setRequest(payload.request || null);
        setHostessLocation(points.hostess);
        setDriverLocation(points.driver);
        setAgePolicy(locationAgePolicy(payload));
        setServerSharingWindow({
          open: typeof payload.sharingWindowOpen === 'boolean' ? payload.sharingWindowOpen : null,
          endsAt: payload.sharingEndsAt || null,
          locationTestModeActive: payload.locationTestModeActive === true,
          locationTestModeEndsAt: payload.locationTestModeEndsAt || null,
          locationTestDriverId: payload.locationTestDriverId || null,
          locationTestDriverName: payload.locationTestDriverName || null
        });
        setError('');
      } catch (requestError) {
        if (active && requestError.name !== 'AbortError') {
          if ([401, 403, 404].includes(requestError.status)) {
            setHostessLocation(null);
            setDriverLocation(null);
          }
          setError(requestError.message);
        }
      } finally {
        requestController = null;
        if (active) setLoading(false);
      }
    }
    loadApproach();
    const timer = window.setInterval(() => {
      if (document.visibilityState === 'visible') loadApproach();
    }, LOCATION_REFRESH_INTERVAL_MS);
    const handleVisibility = () => { if (document.visibilityState === 'visible') loadApproach(); };
    document.addEventListener('visibilitychange', handleVisibility);
    return () => {
      active = false;
      requestController?.abort();
      window.clearInterval(timer);
      document.removeEventListener('visibilitychange', handleVisibility);
    };
  }, [requestId, token, reloadKey]);

  useEffect(() => {
    if (!shareHostessLocation || !requestId) return undefined;
    let active = true;
    let watchId = null;
    let lastSentAt = 0;
    let inFlight = false;
    if (!navigator.geolocation) {
      setSharingError('Este aparelho não oferece localização pelo navegador.');
      return undefined;
    }
    async function sendPosition(position) {
      const now = Date.now();
      if (!active || inFlight || now - lastSentAt < LOCATION_SEND_INTERVAL_MS) return;
      inFlight = true;
      lastSentAt = now;
      try {
        await locationApi(token, `/api/hostess-requests/${requestId}/location`, {
          method: 'PUT',
          body: JSON.stringify({
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
            accuracy: Number.isFinite(position.coords.accuracy) ? position.coords.accuracy : null
          })
        });
        if (active) setSharingError('');
      } catch (requestError) {
        if (active) setSharingError(requestError.message);
      } finally {
        inFlight = false;
      }
    }
    watchId = navigator.geolocation.watchPosition(
      (position) => void sendPosition(position),
      (geolocationError) => { if (active) setSharingError(geolocationErrorMessage(geolocationError)); },
      { enableHighAccuracy: true, maximumAge: 10000, timeout: 20000 }
    );
    return () => {
      active = false;
      if (watchId !== null) navigator.geolocation.clearWatch(watchId);
    };
  }, [requestId, shareHostessLocation, token]);

  const allLocations = [hostessLocation, driverLocation].filter(Boolean);
  const ageNow = useLocationAgeClock(allLocations, [agePolicy.staleAfterSeconds, agePolicy.expiresAfterSeconds]);
  const sharingPeriodClosed = (!locationTestMode.active && !localSharingWindow.open) || serverSharingWindow.open === false;
  const visibleLocations = sharingPeriodClosed ? [] : allLocations.map((location) => {
    const ageState = localLocationAgeState(location, agePolicy, ageNow);
    return ageState === 'expired' ? null : { ...location, stale: ageState === 'stale' };
  }).filter(Boolean);
  const visibleHostess = visibleLocations.find((location) => location.kind === 'hostess');
  const visibleDriver = visibleLocations.find((location) => location.kind === 'driver');
  const distance = distanceBetweenLocations(visibleHostess, visibleDriver);
  const formattedDistance = distanceLabel(distance);
  const movementKey = `${visibleHostess?.updatedAt || ''}|${visibleDriver?.updatedAt || ''}`;
  useEffect(() => {
    if (!Number.isFinite(distance)) {
      previousDistanceRef.current = NaN;
      setMovementLabel('Acompanhando aproximação');
      return;
    }
    const previous = previousDistanceRef.current;
    if (Number.isFinite(previous) && previous - distance >= 10) setMovementLabel('Motorista se aproximando');
    else setMovementLabel('Acompanhando aproximação');
    previousDistanceRef.current = distance;
  }, [movementKey, distance]);

  const assignedDriverName = request?.assignedDriverName || driverLocation?.driverName || '';
  const endLabel = sharingEndLabel(serverSharingWindow.endsAt);
  const heading = assignedDriverName
    ? formattedDistance ? `${assignedDriverName} está a ${formattedDistance} da Hostess` : `${assignedDriverName} aceitou o chamado`
    : 'Aguardando um motorista';
  return <section className="panel driver-map-panel hostess-approach-map">
    <div className="panel-heading"><div><h2>{heading}</h2><p>{assignedDriverName ? 'O mapa mostra a Hostess e o motorista deste chamado para acompanhar a aproximação.' : 'Sua posição ficará pronta para o motorista que aceitar este chamado.'}</p></div><div className="driver-map-heading-actions"><span className="location-map-count" aria-live="polite">{sharingPeriodClosed ? <ShieldCheck size={14} /> : <Radio size={14} />} {sharingPeriodClosed ? `Encerrado às ${endLabel}` : assignedDriverName ? movementLabel : 'Aguardando'}</span>{visibleLocations.length > 0 && <button className="text-button" type="button" onClick={() => setFitRequest((value) => value + 1)}><Navigation size={14} /> Centralizar</button>}</div></div>
    <LocationTestModeNotice testMode={locationTestMode} />
    {sharingError && <div className="driver-map-error" role="alert"><span>{sharingError}</span></div>}
    {error && <div className="driver-map-error" role="alert"><span>{error}</span><button className="text-button" type="button" onClick={() => { setLoading(!visibleLocations.length); setReloadKey((value) => value + 1); }}>Tentar novamente</button></div>}
    {!error && sharingPeriodClosed ? <div className="driver-map-empty"><ShieldCheck size={26} /><div><strong>Período de localização encerrado</strong><span>Os dois pontos ficam ocultos após {endLabel} (horário de Salvador), exceto durante o teste autorizado.</span></div></div> : loading ? <div className="driver-map-empty" role="status"><LoaderCircle className="spin" size={25} /> Preparando acompanhamento…</div> : visibleLocations.length ? <div className="driver-map-layout"><div className="driver-map-frame"><DriverMapCanvas locations={visibleLocations} fitRequest={fitRequest} ariaLabel="Mapa com a localização da Hostess e do motorista em apoio" /></div><div className="location-driver-list approach-location-list" aria-label="Pessoas deste chamado">{visibleLocations.map((location) => <article key={location.driverId} className={`${location.stale ? 'location-stale ' : ''}${location.kind === 'hostess' ? 'location-hostess' : ''}`.trim()}><span className="location-driver-dot" aria-hidden="true" /><div><strong>{location.driverName}</strong><small>{location.kind === 'hostess' ? 'Ponto de encontro' : 'Motorista em deslocamento'} · {location.stale ? 'sinal desatualizado' : locationAge(location.updatedAt)}{Number.isFinite(location.accuracy) ? ` · ±${Math.round(location.accuracy)} m` : ''}</small></div></article>)}{assignedDriverName && !visibleDriver && <article><MapPin size={17} /><div><strong>{assignedDriverName}</strong><small>Ative “Compartilhar minha localização” no celular do motorista.</small></div></article>}</div></div> : <div className="driver-map-empty"><MapPin size={26} /><div><strong>Localização ainda não disponível</strong><span>{shareHostessLocation ? 'Permita a localização deste site para enviar o ponto de encontro.' : 'A Hostess precisa manter o chamado aberto e a localização permitida.'}</span></div></div>}
    <div className="driver-map-privacy"><ShieldCheck size={15} /> A posição da Hostess é temporária e visível apenas para ela e para o motorista que aceitou este chamado. Ela é apagada quando o atendimento termina.</div>
  </section>;
}


const CLOSED_CONSULTANT_REQUEST_STATUSES = new Set(['ENCERRADO', 'CONCLUIDO', 'FECHADO', 'CANCELADO', 'CLOSED', 'EXPIRED']);


function consultantRequestIsClosed(request) {
  if (!request) return false;
  if (request.active === false || request.closedAt) return true;
  return CLOSED_CONSULTANT_REQUEST_STATUSES.has(String(request.status || '').trim().toUpperCase());
}


function scopedRequestLocation(payload, request) {
  const rawLocation = Array.isArray(payload?.locations) ? payload.locations[0] : payload?.location;
  if (!rawLocation) return null;
  return normalizedLocation({
    ...rawLocation,
    driverId: rawLocation.driverId || request?.assignedDriverId || request?.id || 'motorista-do-pedido',
    driverName: rawLocation.driverName || request?.assignedDriverName || 'Motorista em apoio'
  });
}


export function ConsultantSupportLocationPanel({ requestId, accessToken, initialRequest = null, onRequestChange, onUnavailable }) {
  const localSharingWindow = useSalvadorSharingWindow();
  const [request, setRequest] = useState(initialRequest);
  const [location, setLocation] = useState(null);
  const [agePolicy, setAgePolicy] = useState(() => locationAgePolicy(null));
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [reloadKey, setReloadKey] = useState(0);
  const [fitRequest, setFitRequest] = useState(0);
  const [serverSharingWindow, setServerSharingWindow] = useState({
    open: null,
    endsAt: null,
    locationTestModeActive: false,
    locationTestModeEndsAt: null
  });
  const locationTestMode = useLocationTestMode(serverSharingWindow);
  const onRequestChangeRef = useRef(onRequestChange);
  const onUnavailableRef = useRef(onUnavailable);

  useEffect(() => { onRequestChangeRef.current = onRequestChange; }, [onRequestChange]);
  useEffect(() => { onUnavailableRef.current = onUnavailable; }, [onUnavailable]);
  useEffect(() => {
    setRequest(initialRequest);
    setLocation(null);
    setLoading(true);
    setError('');
    setAgePolicy(locationAgePolicy(null));
    setServerSharingWindow({
      open: null,
      endsAt: null,
      locationTestModeActive: false,
      locationTestModeEndsAt: null
    });
  }, [requestId, accessToken]);

  useEffect(() => {
    if (!requestId || !accessToken) return undefined;
    let active = true;
    let requestController = null;
    async function loadRequest() {
      if (requestController) return;
      requestController = new AbortController();
      try {
        const payload = await locationApi('', `/api/public/consultant-support-requests/${encodeURIComponent(requestId)}`, {
          headers: { 'X-Support-Access-Token': accessToken },
          signal: requestController.signal
        });
        if (!active) return;
        const nextRequest = payload.request && typeof payload.request === 'object' ? payload.request : null;
        const serverWindowOpen = typeof payload.sharingWindowOpen === 'boolean' ? payload.sharingWindowOpen : null;
        const nextLocation = scopedRequestLocation(payload, nextRequest);
        setRequest(nextRequest);
        setServerSharingWindow({
          open: serverWindowOpen,
          endsAt: payload.sharingEndsAt || null,
          locationTestModeActive: payload.locationTestModeActive === true,
          locationTestModeEndsAt: payload.locationTestModeEndsAt || null
        });
        setAgePolicy(locationAgePolicy(payload));
        setLocation(serverWindowOpen === false || consultantRequestIsClosed(nextRequest) ? null : nextLocation);
        setError('');
        onRequestChangeRef.current?.(nextRequest);
      } catch (requestError) {
        if (!active || requestError.name === 'AbortError') return;
        // O painel público é fail-closed: sem confirmação atual do servidor,
        // nenhuma coordenada anterior continua desenhada.
        setLocation(null);
        if ([403, 404, 410].includes(requestError.status)) {
          onUnavailableRef.current?.(requestError);
          return;
        }
        setError(requestError.message || 'Não foi possível atualizar este pedido.');
      } finally {
        requestController = null;
        if (active) setLoading(false);
      }
    }
    loadRequest();
    const timer = window.setInterval(() => {
      if (document.visibilityState === 'visible') loadRequest();
    }, LOCATION_REFRESH_INTERVAL_MS);
    const handleVisibility = () => { if (document.visibilityState === 'visible') loadRequest(); };
    document.addEventListener('visibilitychange', handleVisibility);
    return () => {
      active = false;
      requestController?.abort();
      window.clearInterval(timer);
      document.removeEventListener('visibilitychange', handleVisibility);
    };
  }, [requestId, accessToken, reloadKey]);

  const ageNow = useLocationAgeClock(location ? [location] : [], [agePolicy.staleAfterSeconds]);
  const requestClosed = consultantRequestIsClosed(request);
  const sharingPeriodClosed = (!locationTestMode.active && !localSharingWindow.open) || serverSharingWindow.open === false;
  const endLabel = sharingEndLabel(serverSharingWindow.endsAt);
  const assignedDriverName = request?.assignedDriverName || location?.driverName || '';
  const stale = Boolean(location) && localLocationAgeState(location, agePolicy, ageNow) !== 'fresh';
  const visibleLocations = !requestClosed && !sharingPeriodClosed && location && !stale ? [location] : [];
  const requestTime = request?.createdAt ? locationAge(request.createdAt) : '';

  return <section className="panel driver-map-panel consultant-support-map">
    <div className="panel-heading"><div><h2>{requestClosed ? 'Pedido de apoio encerrado' : assignedDriverName ? `${assignedDriverName} está a caminho` : 'Aguardando um motorista'}</h2><p>{requestClosed ? 'Este pedido de apoio foi encerrado.' : assignedDriverName ? 'A posição abaixo pertence somente ao motorista que assumiu este pedido.' : `Seu pedido foi enviado${requestTime ? ` ${requestTime}` : ''}. O mapa será liberado quando um motorista assumir e compartilhar a localização.`}</p></div><div className="driver-map-heading-actions"><span className="location-map-count" aria-live="polite">{requestClosed || sharingPeriodClosed ? <ShieldCheck size={14} /> : <Radio size={14} />} {requestClosed ? 'Pedido encerrado' : sharingPeriodClosed ? `Encerrado às ${endLabel}` : visibleLocations.length ? 'Localização recente' : 'Aguardando'}</span>{visibleLocations.length > 0 && <button className="text-button" type="button" onClick={() => setFitRequest((value) => value + 1)}><Navigation size={14} /> Centralizar</button>}</div></div>
    <LocationTestModeNotice testMode={locationTestMode} />
    {error && <div className="driver-map-error" role="alert"><span>{error}</span><button className="text-button" type="button" onClick={() => { setLoading(!location); setReloadKey((value) => value + 1); }}>Tentar novamente</button></div>}
    {error && !visibleLocations.length ? null : requestClosed ? <div className="driver-map-empty"><ShieldCheck size={26} /><div><strong>Atendimento encerrado</strong><span>Por privacidade, a localização não fica disponível após o fim do pedido.</span></div></div> : sharingPeriodClosed ? <div className="driver-map-empty"><ShieldCheck size={26} /><div><strong>Período de localização encerrado</strong><span>O compartilhamento dos motoristas terminou às {endLabel} (horário de Salvador).</span></div></div> : loading ? <div className="driver-map-empty" role="status"><LoaderCircle className="spin" size={25} /> Atualizando seu pedido…</div> : !assignedDriverName ? <div className="driver-map-empty"><MapPin size={26} /><div><strong>Pedido enviado</strong><span>Assim que um motorista assumir, o acompanhamento deste chamado aparecerá aqui.</span></div></div> : stale ? <div className="driver-map-empty"><MapPin size={26} /><div><strong>Posição temporariamente indisponível</strong><span>O último ponto de {assignedDriverName} ficou desatualizado e foi ocultado.</span></div></div> : !visibleLocations.length ? <div className="driver-map-empty"><MapPin size={26} /><div><strong>{assignedDriverName} ainda não compartilhou a posição</strong><span>{locationTestMode.active ? 'O mapa aparecerá quando houver um sinal recente, após o check-in e durante esta janela temporária de teste.' : 'O mapa aparecerá quando houver um sinal recente, após o check-in e antes das 15:00.'}</span></div></div> : <div className="driver-map-layout consultant-support-map-layout"><div className="driver-map-frame"><DriverMapCanvas locations={visibleLocations} fitRequest={fitRequest} ariaLabel={`Mapa com a localização de ${assignedDriverName} para este pedido de apoio`} /></div><div className="location-driver-list" aria-label="Motorista deste pedido"><article><span className="location-driver-dot" aria-hidden="true" /><div><strong>{assignedDriverName}</strong><small>Localização recente · {locationAge(location.updatedAt)}{Number.isFinite(location.accuracy) ? ` · ±${Math.round(location.accuracy)} m` : ''}</small></div></article></div></div>}
    <div className="driver-map-privacy"><ShieldCheck size={15} /> Acesso temporário e exclusivo deste pedido. Este painel nunca recebe a posição dos outros motoristas; o fundo cartográfico é fornecido pelo OpenStreetMap.</div>
  </section>;
}

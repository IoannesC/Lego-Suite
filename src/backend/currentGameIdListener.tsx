import { setCurrentGameId } from '../redux-modules/extraActions';
import { store } from '../redux-modules/store';
import { extractCurrentGameId } from './utils';

let intervalId: undefined | number;

export const currentGameIdListener = () => {
  intervalId = window.setInterval(() => {
    const {
      ui: { currentGameId: oldGameId }
    } = store.getState();
    const currentGameId = extractCurrentGameId();
    if (oldGameId !== currentGameId) {
      store.dispatch(setCurrentGameId(currentGameId));
    }
  }, 1000);

  return () => {
    if (intervalId) clearInterval(intervalId);
  };
};

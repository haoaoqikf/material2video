import {expect, it} from 'vitest';
import {styleAt} from './styles';

it('interpolates CSS styles purely', () => {
  expect(styleAt(0.5, {opacity: 0}, {opacity: 1}, t => t)).toEqual({opacity: 0.5});
});

import {render,screen} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import {describe,it,expect} from 'vitest';
import {featureDirectory,FeaturesPage} from '../pages/FeaturesPage';

describe('feature directory',()=>{
  it('shows the complete supported and planned feature list without a session',()=>{
    render(<MemoryRouter><FeaturesPage guest/></MemoryRouter>);
    for(const feature of featureDirectory)expect(screen.getByRole('heading',{name:feature.title})).toBeInTheDocument();
    expect(screen.getByText(/Not for actual patient information/)).toBeInTheDocument();
    expect(screen.getByRole('link',{name:/Return to sign in/})).toHaveAttribute('href','/');
  });
  it('does not present unconnected services as operational',()=>{
    expect(featureDirectory.filter(f=>!f.available).map(f=>f.title)).toEqual(['Appointments','Care-team messages']);
  });
});

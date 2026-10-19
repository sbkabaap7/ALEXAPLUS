import {type ReactNode} from 'react';
import FadingVideo from './FadingVideo';
import heroVideo from '../assets/hero-space.mp4';
import heroPoster from '../assets/hero-poster.png';

export default function CinematicHome({children}:{children:ReactNode}){
 return <div className="cinematic-home"><section className="scene-section home-hero">
  <FadingVideo src={heroVideo} poster={heroPoster} className="hero-video"/>
  <div className="hero-content">{children}</div>
 </section></div>;
}

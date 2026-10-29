import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';

import { ProfileComponent } from './profile';

describe('ProfileComponent', () => {
  let component: ProfileComponent;
  let fixture: ComponentFixture<ProfileComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ProfileComponent],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ProfileComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('manda a crear el proyecto si el gerente todavía no tiene uno', () => {
    component.perfil = { proyecto: undefined };
    expect(component.rutaNuevaOferta).toEqual(['/formcreateproyect']);

    component.perfil = { proyecto: { id: 'abc' } };
    expect(component.rutaNuevaOferta).toEqual(['/formcreatecontract', 'abc']);
  });

  it('renderiza el perfil de un gerente sin proyecto', () => {
    component.perfil = { email: 'empresa@udela.edu.ar', nombre: 'Ana', apellido: 'Paz', proyecto: undefined };
    component.rolActual = 'gerente';
    component.isOwnProfile = true;

    expect(() => fixture.detectChanges()).not.toThrow();
    expect(fixture.nativeElement.textContent).toContain('Todavía no creaste tu proyecto');

    component.isEditing = true;
    expect(() => fixture.detectChanges()).not.toThrow();
  });
});

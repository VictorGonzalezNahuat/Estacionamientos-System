import { ComponentFixture, TestBed } from '@angular/core/testing';

import { DescargaDocumentos } from './descarga-documentos';

describe('DescargaDocumentos', () => {
  let component: DescargaDocumentos;
  let fixture: ComponentFixture<DescargaDocumentos>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DescargaDocumentos]
    })
    .compileComponents();

    fixture = TestBed.createComponent(DescargaDocumentos);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});

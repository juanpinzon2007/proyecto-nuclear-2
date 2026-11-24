import { computed, signal } from '@angular/core';
import { MatPaginatorIntl, PageEvent } from '@angular/material/paginator';

export function paginadorEnEspanol(): MatPaginatorIntl {
  const intl = new MatPaginatorIntl();
  intl.itemsPerPageLabel = 'Elementos por página';
  intl.nextPageLabel = 'Página siguiente';
  intl.previousPageLabel = 'Página anterior';
  intl.firstPageLabel = 'Primera página';
  intl.lastPageLabel = 'Última página';
  intl.getRangeLabel = (pagina, tamano, total) => {
    if (!total || !tamano) return `0 de ${total}`;
    return `${pagina * tamano + 1}–${Math.min((pagina + 1) * tamano, total)} de ${total}`;
  };
  return intl;
}

function normalizar(texto: string): string {
  return texto.normalize('NFD').replace(/\p{Diacritic}/gu, '').toLocaleLowerCase('es').trim();
}

export function etiquetaEstado(valor: string): string {
  if (valor === 'TECNICO') return 'Técnico';
  if (valor === 'RUBRICA_V1') return 'Rúbrica v1';
  const texto = valor.toLocaleLowerCase('es').replaceAll('_', ' ');
  return texto.charAt(0).toLocaleUpperCase('es') + texto.slice(1);
}

export class ListaPaginada<T> {
  readonly busqueda = signal('');
  readonly tamano = signal(10);
  private readonly paginaSolicitada = signal(0);

  readonly filtrados = computed(() => {
    const termino = normalizar(this.busqueda());
    const filas = this.fuente();
    return termino ? filas.filter((fila) => normalizar(this.texto(fila)).includes(termino)) : filas;
  });
  readonly pagina = computed(() =>
    Math.min(this.paginaSolicitada(), Math.max(0, Math.ceil(this.filtrados().length / this.tamano()) - 1)),
  );
  readonly visibles = computed(() => {
    const inicio = this.pagina() * this.tamano();
    return this.filtrados().slice(inicio, inicio + this.tamano());
  });

  constructor(private readonly fuente: () => readonly T[], private readonly texto: (fila: T) => string) {}

  buscar(texto: string): void {
    this.busqueda.set(texto);
    this.paginaSolicitada.set(0);
  }

  cambiar(evento: PageEvent): void {
    this.tamano.set(evento.pageSize);
    this.paginaSolicitada.set(evento.pageIndex);
  }
}

export default function({data, parentElement, setTriggerValue}) {
  const root = parentElement.querySelector('.rp-calendar');
  root.replaceChildren();
  const make = (tag, text, cls) => {
    const el = document.createElement(tag);
    if (text !== undefined) el.textContent = text;
    if (cls) el.className = cls;
    return el;
  };
  const emit = (type, day) => setTriggerValue('action', {type, day, month:data.month});
  const header = make('div', undefined, 'month-header');
  const title = make('h3', data.title);
  header.append(title);
  const controls = make('div', undefined, 'month-controls');
  for (const [type, text] of [['previous','‹'],['today',data.labels.today],['next','›']]) {
    const button = make('button',text,type==='today'?'today-control':'arrow-control');
    button.type = 'button';
    button.setAttribute('aria-label',data.labels[type]);
    button.onclick = () => emit(type);
    controls.append(button);
  }
  header.append(controls); root.append(header);
  const weekdays = make('div',undefined,'weekdays');
  weekdays.setAttribute('aria-hidden','true');
  data.weekdays.forEach(name => weekdays.append(make('span',name)));
  root.append(weekdays);
  const grid = make('div',undefined,'day-grid');
  grid.setAttribute('role','group'); grid.setAttribute('aria-label',data.labels.calendar);
  const buttons = [];
  data.days.forEach((day,index) => {
    const button = make('button',undefined,'day'+(day.inMonth?'':' outside')+(day.today?' is-today':'')+(day.selected?' selected':''));
    button.type='button'; button.dataset.date=day.iso;
    button.setAttribute('aria-label',day.label); button.setAttribute('aria-pressed',String(day.selected));
    button.tabIndex=day.selected?0:-1;
    button.append(make('span',String(day.number),'number'));
    const dots=make('span',undefined,'dots');
    for (const kind of ['plan','note','study','analysis']) {
      if (day.counts[kind]) dots.append(make('i',undefined,kind));
    }
    dots.setAttribute('aria-hidden','true'); button.append(dots);
    button.onclick=()=>emit('day',day.iso);
    button.onkeydown=(event)=>{
      const offsets={ArrowLeft:-1,ArrowRight:1,ArrowUp:-7,ArrowDown:7};
      if (event.key in offsets) {
        event.preventDefault(); const next=index+offsets[event.key];
        if(buttons[next]) {button.tabIndex=-1; buttons[next].tabIndex=0;buttons[next].focus();}
      }
    };
    buttons.push(button); grid.append(button);
  });
  root.append(grid);
}

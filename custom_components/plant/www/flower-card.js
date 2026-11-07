/*! For license information please see flower-card.js.LICENSE.txt */
(()=>{"use strict";const t=globalThis,e=t.ShadowRoot&&(void 0===t.ShadyCSS||t.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,i=Symbol(),s=new WeakMap;class n{constructor(t,e,s){if(this._$cssResult$=!0,s!==i)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t,this.t=e}get styleSheet(){let t=this.o;const i=this.t;if(e&&void 0===t){const e=void 0!==i&&1===i.length;e&&(t=s.get(i)),void 0===t&&((this.o=t=new CSSStyleSheet).replaceSync(this.cssText),e&&s.set(i,t))}return t}toString(){return this.cssText}}const a=(i,s)=>{if(e)i.adoptedStyleSheets=s.map(t=>t instanceof CSSStyleSheet?t:t.styleSheet);else for(const e of s){const s=document.createElement("style"),n=t.litNonce;void 0!==n&&s.setAttribute("nonce",n),s.textContent=e.cssText,i.appendChild(s)}},o=e?t=>t:t=>t instanceof CSSStyleSheet?(t=>{let e="";for(const i of t.cssRules)e+=i.cssText;return(t=>new n("string"==typeof t?t:t+"",void 0,i))(e)})(t):t,{is:r,defineProperty:l,getOwnPropertyDescriptor:c,getOwnPropertyNames:d,getOwnPropertySymbols:h,getPrototypeOf:p}=Object,u=globalThis,g=u.trustedTypes,m=g?g.emptyScript:"",_=u.reactiveElementPolyfillSupport,f=(t,e)=>t,v={toAttribute(t,e){switch(e){case Boolean:t=t?m:null;break;case Object:case Array:t=null==t?t:JSON.stringify(t)}return t},fromAttribute(t,e){let i=t;switch(e){case Boolean:i=null!==t;break;case Number:i=null===t?null:Number(t);break;case Object:case Array:try{i=JSON.parse(t)}catch(t){i=null}}return i}},y=(t,e)=>!r(t,e),b={attribute:!0,type:String,converter:v,reflect:!1,useDefault:!1,hasChanged:y};Symbol.metadata??=Symbol("metadata"),u.litPropertyMetadata??=new WeakMap;class $ extends HTMLElement{static addInitializer(t){this._$Ei(),(this.l??=[]).push(t)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(t,e=b){if(e.state&&(e.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(t)&&((e=Object.create(e)).wrapped=!0),this.elementProperties.set(t,e),!e.noAccessor){const i=Symbol(),s=this.getPropertyDescriptor(t,i,e);void 0!==s&&l(this.prototype,t,s)}}static getPropertyDescriptor(t,e,i){const{get:s,set:n}=c(this.prototype,t)??{get(){return this[e]},set(t){this[e]=t}};return{get:s,set(e){const a=s?.call(this);n?.call(this,e),this.requestUpdate(t,a,i)},configurable:!0,enumerable:!0}}static getPropertyOptions(t){return this.elementProperties.get(t)??b}static _$Ei(){if(this.hasOwnProperty(f("elementProperties")))return;const t=p(this);t.finalize(),void 0!==t.l&&(this.l=[...t.l]),this.elementProperties=new Map(t.elementProperties)}static finalize(){if(this.hasOwnProperty(f("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(f("properties"))){const t=this.properties,e=[...d(t),...h(t)];for(const i of e)this.createProperty(i,t[i])}const t=this[Symbol.metadata];if(null!==t){const e=litPropertyMetadata.get(t);if(void 0!==e)for(const[t,i]of e)this.elementProperties.set(t,i)}this._$Eh=new Map;for(const[t,e]of this.elementProperties){const i=this._$Eu(t,e);void 0!==i&&this._$Eh.set(i,t)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(t){const e=[];if(Array.isArray(t)){const i=new Set(t.flat(1/0).reverse());for(const t of i)e.unshift(o(t))}else void 0!==t&&e.push(o(t));return e}static _$Eu(t,e){const i=e.attribute;return!1===i?void 0:"string"==typeof i?i:"string"==typeof t?t.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(t=>this.enableUpdating=t),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(t=>t(this))}addController(t){(this._$EO??=new Set).add(t),void 0!==this.renderRoot&&this.isConnected&&t.hostConnected?.()}removeController(t){this._$EO?.delete(t)}_$E_(){const t=new Map,e=this.constructor.elementProperties;for(const i of e.keys())this.hasOwnProperty(i)&&(t.set(i,this[i]),delete this[i]);t.size>0&&(this._$Ep=t)}createRenderRoot(){const t=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return a(t,this.constructor.elementStyles),t}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(t=>t.hostConnected?.())}enableUpdating(t){}disconnectedCallback(){this._$EO?.forEach(t=>t.hostDisconnected?.())}attributeChangedCallback(t,e,i){this._$AK(t,i)}_$ET(t,e){const i=this.constructor.elementProperties.get(t),s=this.constructor._$Eu(t,i);if(void 0!==s&&!0===i.reflect){const n=(void 0!==i.converter?.toAttribute?i.converter:v).toAttribute(e,i.type);this._$Em=t,null==n?this.removeAttribute(s):this.setAttribute(s,n),this._$Em=null}}_$AK(t,e){const i=this.constructor,s=i._$Eh.get(t);if(void 0!==s&&this._$Em!==s){const t=i.getPropertyOptions(s),n="function"==typeof t.converter?{fromAttribute:t.converter}:void 0!==t.converter?.fromAttribute?t.converter:v;this._$Em=s;const a=n.fromAttribute(e,t.type);this[s]=a??this._$Ej?.get(s)??a,this._$Em=null}}requestUpdate(t,e,i,s=!1,n){if(void 0!==t){const a=this.constructor;if(!1===s&&(n=this[t]),i??=a.getPropertyOptions(t),!((i.hasChanged??y)(n,e)||i.useDefault&&i.reflect&&n===this._$Ej?.get(t)&&!this.hasAttribute(a._$Eu(t,i))))return;this.C(t,e,i)}!1===this.isUpdatePending&&(this._$ES=this._$EP())}C(t,e,{useDefault:i,reflect:s,wrapped:n},a){i&&!(this._$Ej??=new Map).has(t)&&(this._$Ej.set(t,a??e??this[t]),!0!==n||void 0!==a)||(this._$AL.has(t)||(this.hasUpdated||i||(e=void 0),this._$AL.set(t,e)),!0===s&&this._$Em!==t&&(this._$Eq??=new Set).add(t))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(t){Promise.reject(t)}const t=this.scheduleUpdate();return null!=t&&await t,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(const[t,e]of this._$Ep)this[t]=e;this._$Ep=void 0}const t=this.constructor.elementProperties;if(t.size>0)for(const[e,i]of t){const{wrapped:t}=i,s=this[e];!0!==t||this._$AL.has(e)||void 0===s||this.C(e,void 0,i,s)}}let t=!1;const e=this._$AL;try{t=this.shouldUpdate(e),t?(this.willUpdate(e),this._$EO?.forEach(t=>t.hostUpdate?.()),this.update(e)):this._$EM()}catch(e){throw t=!1,this._$EM(),e}t&&this._$AE(e)}willUpdate(t){}_$AE(t){this._$EO?.forEach(t=>t.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(t)),this.updated(t)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(t){return!0}update(t){this._$Eq&&=this._$Eq.forEach(t=>this._$ET(t,this[t])),this._$EM()}updated(t){}firstUpdated(t){}}$.elementStyles=[],$.shadowRootOptions={mode:"open"},$[f("elementProperties")]=new Map,$[f("finalized")]=new Map,_?.({ReactiveElement:$}),(u.reactiveElementVersions??=[]).push("2.1.2");const w=globalThis,x=t=>t,A=w.trustedTypes,M=A?A.createPolicy("lit-html",{createHTML:t=>t}):void 0,S="$lit$",E=`lit$${Math.random().toFixed(9).slice(2)}$`,D="?"+E,C=`<${D}>`,N=document,L=()=>N.createComment(""),I=t=>null===t||"object"!=typeof t&&"function"!=typeof t,k=Array.isArray,O="[ \t\n\f\r]",j=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,U=/-->/g,P=/>/g,T=RegExp(`>|${O}(?:([^\\s"'>=/]+)(${O}*=${O}*(?:[^ \t\n\f\r"'\`<>=]|("|')|))|$)`,"g"),z=/'/g,H=/"/g,R=/^(?:script|style|textarea|title)$/i,B=t=>(e,...i)=>({_$litType$:t,strings:e,values:i}),F=B(1),W=(B(2),B(3),Symbol.for("lit-noChange")),V=Symbol.for("lit-nothing"),Q=new WeakMap,Z=N.createTreeWalker(N,129);function Y(t,e){if(!k(t)||!t.hasOwnProperty("raw"))throw Error("invalid template strings array");return void 0!==M?M.createHTML(e):e}const q=(t,e)=>{const i=t.length-1,s=[];let n,a=2===e?"<svg>":3===e?"<math>":"",o=j;for(let e=0;e<i;e++){const i=t[e];let r,l,c=-1,d=0;for(;d<i.length&&(o.lastIndex=d,l=o.exec(i),null!==l);)d=o.lastIndex,o===j?"!--"===l[1]?o=U:void 0!==l[1]?o=P:void 0!==l[2]?(R.test(l[2])&&(n=RegExp("</"+l[2],"g")),o=T):void 0!==l[3]&&(o=T):o===T?">"===l[0]?(o=n??j,c=-1):void 0===l[1]?c=-2:(c=o.lastIndex-l[2].length,r=l[1],o=void 0===l[3]?T:'"'===l[3]?H:z):o===H||o===z?o=T:o===U||o===P?o=j:(o=T,n=void 0);const h=o===T&&t[e+1].startsWith("/>")?" ":"";a+=o===j?i+C:c>=0?(s.push(r),i.slice(0,c)+S+i.slice(c)+E+h):i+E+(-2===c?e:h)}return[Y(t,a+(t[i]||"<?>")+(2===e?"</svg>":3===e?"</math>":"")),s]};class X{constructor({strings:t,_$litType$:e},i){let s;this.parts=[];let n=0,a=0;const o=t.length-1,r=this.parts,[l,c]=q(t,e);if(this.el=X.createElement(l,i),Z.currentNode=this.el.content,2===e||3===e){const t=this.el.content.firstChild;t.replaceWith(...t.childNodes)}for(;null!==(s=Z.nextNode())&&r.length<o;){if(1===s.nodeType){if(s.hasAttributes())for(const t of s.getAttributeNames())if(t.endsWith(S)){const e=c[a++],i=s.getAttribute(t).split(E),o=/([.?@])?(.*)/.exec(e);r.push({type:1,index:n,name:o[2],strings:i,ctor:"."===o[1]?et:"?"===o[1]?it:"@"===o[1]?st:tt}),s.removeAttribute(t)}else t.startsWith(E)&&(r.push({type:6,index:n}),s.removeAttribute(t));if(R.test(s.tagName)){const t=s.textContent.split(E),e=t.length-1;if(e>0){s.textContent=A?A.emptyScript:"";for(let i=0;i<e;i++)s.append(t[i],L()),Z.nextNode(),r.push({type:2,index:++n});s.append(t[e],L())}}}else if(8===s.nodeType)if(s.data===D)r.push({type:2,index:n});else{let t=-1;for(;-1!==(t=s.data.indexOf(E,t+1));)r.push({type:7,index:n}),t+=E.length-1}n++}}static createElement(t,e){const i=N.createElement("template");return i.innerHTML=t,i}}function J(t,e,i=t,s){if(e===W)return e;let n=void 0!==s?i._$Co?.[s]:i._$Cl;const a=I(e)?void 0:e._$litDirective$;return n?.constructor!==a&&(n?._$AO?.(!1),void 0===a?n=void 0:(n=new a(t),n._$AT(t,i,s)),void 0!==s?(i._$Co??=[])[s]=n:i._$Cl=n),void 0!==n&&(e=J(t,n._$AS(t,e.values),n,s)),e}class G{constructor(t,e){this._$AV=[],this._$AN=void 0,this._$AD=t,this._$AM=e}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(t){const{el:{content:e},parts:i}=this._$AD,s=(t?.creationScope??N).importNode(e,!0);Z.currentNode=s;let n=Z.nextNode(),a=0,o=0,r=i[0];for(;void 0!==r;){if(a===r.index){let e;2===r.type?e=new K(n,n.nextSibling,this,t):1===r.type?e=new r.ctor(n,r.name,r.strings,this,t):6===r.type&&(e=new nt(n,this,t)),this._$AV.push(e),r=i[++o]}a!==r?.index&&(n=Z.nextNode(),a++)}return Z.currentNode=N,s}p(t){let e=0;for(const i of this._$AV)void 0!==i&&(void 0!==i.strings?(i._$AI(t,i,e),e+=i.strings.length-2):i._$AI(t[e])),e++}}class K{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(t,e,i,s){this.type=2,this._$AH=V,this._$AN=void 0,this._$AA=t,this._$AB=e,this._$AM=i,this.options=s,this._$Cv=s?.isConnected??!0}get parentNode(){let t=this._$AA.parentNode;const e=this._$AM;return void 0!==e&&11===t?.nodeType&&(t=e.parentNode),t}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(t,e=this){t=J(this,t,e),I(t)?t===V||null==t||""===t?(this._$AH!==V&&this._$AR(),this._$AH=V):t!==this._$AH&&t!==W&&this._(t):void 0!==t._$litType$?this.$(t):void 0!==t.nodeType?this.T(t):(t=>k(t)||"function"==typeof t?.[Symbol.iterator])(t)?this.k(t):this._(t)}O(t){return this._$AA.parentNode.insertBefore(t,this._$AB)}T(t){this._$AH!==t&&(this._$AR(),this._$AH=this.O(t))}_(t){this._$AH!==V&&I(this._$AH)?this._$AA.nextSibling.data=t:this.T(N.createTextNode(t)),this._$AH=t}$(t){const{values:e,_$litType$:i}=t,s="number"==typeof i?this._$AC(t):(void 0===i.el&&(i.el=X.createElement(Y(i.h,i.h[0]),this.options)),i);if(this._$AH?._$AD===s)this._$AH.p(e);else{const t=new G(s,this),i=t.u(this.options);t.p(e),this.T(i),this._$AH=t}}_$AC(t){let e=Q.get(t.strings);return void 0===e&&Q.set(t.strings,e=new X(t)),e}k(t){k(this._$AH)||(this._$AH=[],this._$AR());const e=this._$AH;let i,s=0;for(const n of t)s===e.length?e.push(i=new K(this.O(L()),this.O(L()),this,this.options)):i=e[s],i._$AI(n),s++;s<e.length&&(this._$AR(i&&i._$AB.nextSibling,s),e.length=s)}_$AR(t=this._$AA.nextSibling,e){for(this._$AP?.(!1,!0,e);t!==this._$AB;){const e=x(t).nextSibling;x(t).remove(),t=e}}setConnected(t){void 0===this._$AM&&(this._$Cv=t,this._$AP?.(t))}}class tt{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(t,e,i,s,n){this.type=1,this._$AH=V,this._$AN=void 0,this.element=t,this.name=e,this._$AM=s,this.options=n,i.length>2||""!==i[0]||""!==i[1]?(this._$AH=Array(i.length-1).fill(new String),this.strings=i):this._$AH=V}_$AI(t,e=this,i,s){const n=this.strings;let a=!1;if(void 0===n)t=J(this,t,e,0),a=!I(t)||t!==this._$AH&&t!==W,a&&(this._$AH=t);else{const s=t;let o,r;for(t=n[0],o=0;o<n.length-1;o++)r=J(this,s[i+o],e,o),r===W&&(r=this._$AH[o]),a||=!I(r)||r!==this._$AH[o],r===V?t=V:t!==V&&(t+=(r??"")+n[o+1]),this._$AH[o]=r}a&&!s&&this.j(t)}j(t){t===V?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,t??"")}}class et extends tt{constructor(){super(...arguments),this.type=3}j(t){this.element[this.name]=t===V?void 0:t}}class it extends tt{constructor(){super(...arguments),this.type=4}j(t){this.element.toggleAttribute(this.name,!!t&&t!==V)}}class st extends tt{constructor(t,e,i,s,n){super(t,e,i,s,n),this.type=5}_$AI(t,e=this){if((t=J(this,t,e,0)??V)===W)return;const i=this._$AH,s=t===V&&i!==V||t.capture!==i.capture||t.once!==i.once||t.passive!==i.passive,n=t!==V&&(i===V||s);s&&this.element.removeEventListener(this.name,this,i),n&&this.element.addEventListener(this.name,this,t),this._$AH=t}handleEvent(t){"function"==typeof this._$AH?this._$AH.call(this.options?.host??this.element,t):this._$AH.handleEvent(t)}}class nt{constructor(t,e,i){this.element=t,this.type=6,this._$AN=void 0,this._$AM=e,this.options=i}get _$AU(){return this._$AM._$AU}_$AI(t){J(this,t)}}const at=w.litHtmlPolyfillSupport;at?.(X,K),(w.litHtmlVersions??=[]).push("3.3.3");const ot=globalThis;class rt extends ${constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){const t=super.createRenderRoot();return this.renderOptions.renderBefore??=t.firstChild,t}update(t){const e=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(t),this._$Do=((t,e,i)=>{const s=i?.renderBefore??e;let n=s._$litPart$;if(void 0===n){const t=i?.renderBefore??null;s._$litPart$=n=new K(e.insertBefore(L(),t),t,void 0,i??{})}return n._$AI(t),n})(e,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return W}}rt._$litElement$=!0,rt.finalized=!0,ot.litElementHydrateSupport?.({LitElement:rt});const lt=ot.litElementPolyfillSupport;lt?.({LitElement:rt}),(ot.litElementVersions??=[]).push("4.2.2");const ct={attribute:!0,type:String,converter:v,reflect:!1,hasChanged:y},dt=(t=ct,e,i)=>{const{kind:s,metadata:n}=i;let a=globalThis.litPropertyMetadata.get(n);if(void 0===a&&globalThis.litPropertyMetadata.set(n,a=new Map),"setter"===s&&((t=Object.create(t)).wrapped=!0),a.set(i.name,t),"accessor"===s){const{name:s}=i;return{set(i){const n=e.get.call(this);e.set.call(this,i),this.requestUpdate(s,n,t,!0,i)},init(e){return void 0!==e&&this.C(s,void 0,t,e),e}}}if("setter"===s){const{name:s}=i;return function(i){const n=this[s];e.call(this,i),this.requestUpdate(s,n,t,!0,i)}}throw Error("Unsupported decorator location: "+s)};function ht(t){return(e,i)=>"object"==typeof i?dt(t,e,i):((t,e,i)=>{const s=e.hasOwnProperty(i);return e.constructor.createProperty(i,t),s?Object.getOwnPropertyDescriptor(e,i):void 0})(t,e,i)}function pt(t){return ht({...t,state:!0,attribute:!1})}const ut=((t,...e)=>{const s=1===t.length?t[0]:e.reduce((e,i,s)=>e+(t=>{if(!0===t._$cssResult$)return t.cssText;if("number"==typeof t)return t;throw Error("Value passed to 'css' function must be a 'css' function result: "+t+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(i)+t[s+1],t[0]);return new n(s,t,i)})`
.card-margin-top {
  margin-top: 32px;
}
.attributes {
  display: flex;
  white-space: nowrap;
  padding: 8px;
}
.attributes.width-100 {
  padding: 2px;

}
.attribute ha-icon {
  margin-right: 10px;
  margin-left: 5px;
}
.attribute {
  white-space: nowrap;
  display: flex;  
  align-items: center;
  width: 50%;
}
#battery {
  float: right;
  display: flex;
  align-items: center;
  gap: 4px;
  margin-right: 16px;
  margin-top: -15px;
}
.header {
  padding-top: 8px;
  height: 72px;
}
.header-compact {
  padding-top: 4px;
  height: 55px;
}
.attribute .header, .attribute .header-compact {
  height: auto;
  padding-top: 0px;
}
.header > img {
  border-radius: 50%;
  width: 88px;
  height: 88px;
  object-fit: cover;
  margin-left: 16px;
  margin-right: 16px;
  margin-top: -32px;
  float: left;
  box-shadow: var( --ha-card-box-shadow, 0 2px 2px 0 rgba(0, 0, 0, 0.14), 0 1px 5px 0 rgba(0, 0, 0, 0.12), 0 3px 1px -2px rgba(0, 0, 0, 0.2) );
}
.header-compact > img {
  border-radius: 50%;
  width: 50px;
  height: 50px;
  object-fit: cover;
  margin-left: 8px;
  margin-right: 8px;
  margin-top: 0px;
  float: left;
  box-shadow: var( --ha-card-box-shadow, 0 2px 2px 0 rgba(0, 0, 0, 0.14), 0 1px 5px 0 rgba(0, 0, 0, 0.12), 0 3px 1px -2px rgba(0, 0, 0, 0.2) );
}
.header.no-image {
  height: auto;
  padding: 16px;
}
.header.no-image + .divider {
  margin-top: 0;
}
.header-compact.no-image {
  height: auto;
  padding: 8px 16px;
}
.header.no-image > #name,
.header-compact.no-image > #name {
  margin-top: 0;
  margin-left: 0;
}
.header > #name {
  font-weight: bold;
  width: 100%;
  margin-top: 16px;
  display: block;
}
.header-compact > #name {
  font-weight: bold;
  width: 100%;
  margin-top: 8px;
  display: block;
  white-space: nowrap;
}
#name ha-icon {
    color: rgb(240, 163, 163);
}
.header > #species {
  color: #8c96a5;
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.header-compact > #species {
  line-height: 85%;
  color: #8c96a5;
  font-size: 0.8em;
  margin-top: 0px;
  margin-right: 4px;
  opacity: 0.4;
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.meter {
  height: 8px;
  background-color: var(--primary-background-color);
  border-radius: 2px;
  display: inline-grid;
  overflow: hidden;
}
.meter.red {
  flex-grow: 1;
  margin-right: 5px;
  max-width: 5%
}
.meter-wrap {
  flex-grow: 10;
  margin-right: 5px;
  max-width: 40%;
  position: relative;
  display: inline-grid;
}
.attribute.tooltip.width-100 .meter-wrap {
  max-width: 90%;
}
.attribute.tooltip.width-100.has-units .meter-wrap {
  max-width: 70%;
}
.attribute.has-limits {
  padding-bottom: 12px;
}
.meter-wrap > .limits {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  display: flex;
  justify-content: space-between;
  /* A short bar is narrower than its two labels; keep them apart. */
  gap: 0.6em;
  white-space: nowrap;
  font-size: 0.7em;
  line-height: 1.4;
  color: var(--secondary-text-color);
}
.meter > span {
  grid-row: 1;
  grid-column: 1;
  height: 100%;
}
.meter > .good {
  background-color: rgba(43,194,83,1);
}
.meter > .bad {
  background-color: rgba(240,163,163);
}
.meter > .unavailable {
  background-color: rgba(158,158,158,1);
}
.divider {
  height: 1px;
  background-color: #727272;
  opacity: 0.25;
  margin-left: 8px;
  margin-right: 8px;
}
.tooltip {
  position: relative;
}
.tooltip .tip {
  opacity: 0;
  visibility: hidden;
  position: absolute;
  padding: 6px 10px;
  top: 3.3em;
  left: 50%;
  -webkit-transform: translateX(-50%) translateY(-180%);
          transform: translateX(-50%) translateY(-180%);
  background: grey;
  color: white;
  white-space: nowrap;
  z-index: 2;
  border-radius: 2px;
  transition: opacity 0.2s cubic-bezier(0.64, 0.09, 0.08, 1), -webkit-transform 0.2s cubic-bezier(0.64, 0.09, 0.08, 1);
  transition: opacity 0.2s cubic-bezier(0.64, 0.09, 0.08, 1), transform 0.2s cubic-bezier(0.64, 0.09, 0.08, 1);
  transition: opacity 0.2s cubic-bezier(0.64, 0.09, 0.08, 1), transform 0.2s cubic-bezier(0.64, 0.09, 0.08, 1), -webkit-transform 0.2s cubic-bezier(0.64, 0.09, 0.08, 1);
}
.battery.tooltip .tip {
  top: 2em;
}
.extra-badge {
  display: inline-block;
  margin-right: 8px;
  cursor: pointer;
}
.extra-badge .badge-text {
  font-size: 0.9em;
  margin-left: 2px;
  vertical-align: middle;
}
.extra-badge.tooltip .tip {
  top: 2em;
}
.tooltip:hover .tip, .tooltip:active .tip {
  display: block;
  opacity: 1;
  visibility: visible;
  -webkit-transform: translateX(-50%) translateY(-200%);
          transform: translateX(-50%) translateY(-200%);
}
.width-100 {
  width: 100%;
  margin-bottom: 3px;
  margin-right: 5px;
}
@media (max-width: 600px) {
  .header > .unit {
    display: none;
  }
}
.care-info {
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.care-item {
  display: flex;
  flex-direction: column;
}
.care-heading {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 500;
  margin-bottom: 2px;
}
.care-heading ha-icon {
  color: var(--secondary-text-color);
}
.care-text {
  white-space: normal;
  overflow-wrap: break-word;
  line-height: 1.4;
  color: var(--secondary-text-color);
}
.care-info--dialog {
  padding: 4px 4px 8px;
}
.care-info-empty {
  padding: 8px 4px;
  color: var(--secondary-text-color);
}
.has-lightbox {
  cursor: pointer;
}
.image-dialog {
  display: flex;
  flex-direction: column;
  align-items: center;
}
.image-dialog img {
  max-width: 100%;
  max-height: 80vh;
  object-fit: contain;
}
.image-dialog-caption {
  margin-top: 8px;
  text-align: center;
  color: var(--primary-text-color);
  font-weight: 500;
}
`;var gt,mt,_t;!function(t){t.Full="full",t.Compact="compact"}(gt||(gt={})),function(t){t.language="language",t.system="system",t.comma_decimal="comma_decimal",t.decimal_comma="decimal_comma",t.space_comma="space_comma",t.none="none"}(mt||(mt={})),function(t){t.language="language",t.system="system",t.am_pm="12",t.twenty_four="24"}(_t||(_t={}));const ft=(t,e)=>{const i=Object.assign({maximumFractionDigits:2},e);if("string"!=typeof t)return i;if(!e||!e.minimumFractionDigits&&!e.maximumFractionDigits){const e=t.indexOf(".")>-1?t.split(".")[1].length:0;i.minimumFractionDigits=e,i.maximumFractionDigits=e}return i},vt=(new Set(["fan","input_boolean","light","switch","group","automation"]),(t,e,i,s)=>{s=s||{},i=i??{};const n=new Event(e,{bubbles:void 0===s.bubbles||s.bubbles,cancelable:Boolean(s.cancelable),composed:void 0===s.composed||s.composed});return n.detail=i,t.dispatchEvent(n),n});new Set(["call-service","divider","section","weblink","cast","select"]);const yt={en:JSON.parse('{"moisture":"Soil moisture","conductivity":"Conductivity","temperature":"Temperature","illuminance":"Illuminance","humidity":"Air humidity","dli":"Daily light integral","dli_24h":"DLI (24h rolling)","co2":"CO2","soil_temperature":"Soil temperature","vpd":"Vapour pressure deficit","care":"Care","care_watering":"Watering","care_sunlight":"Sunlight","care_soil":"Soil","care_pruning":"Pruning","care_fertilization":"Fertilization","no_care_info":"No care information available.","settings_bars":"Bars","settings_care_info":"Care Info","settings_appearance":"Appearance","settings_entity":"Entity","settings_display_name":"Display Name","settings_display_type":"Display Type","settings_battery_sensor":"Battery Sensor","settings_show_bars":"Show Bars","settings_show_care_info":"Show Care Info","settings_hide_species":"Hide Species","settings_hide_image":"Hide Image","settings_hide_units":"Hide Units","settings_show_limits":"Show Min/Max Values","settings_full":"Full","settings_compact":"Compact"}'),de:JSON.parse('{"moisture":"Bodenfeuchtigkeit","conductivity":"Leitfähigkeit","temperature":"Temperatur","illuminance":"Beleuchtungsstärke","humidity":"Luftfeuchtigkeit","dli":"Tägliches Lichtintegral","dli_24h":"DLI (24h rollierend)","co2":"CO2","soil_temperature":"Bodentemperatur","vpd":"Dampfdruckdefizit","care":"Pflege","care_watering":"Bewässerung","care_sunlight":"Sonnenlicht","care_soil":"Erde","care_pruning":"Rückschnitt","care_fertilization":"Düngung","no_care_info":"Keine Pflegeinformationen verfügbar.","settings_bars":"Balken","settings_care_info":"Pflegeinfo","settings_appearance":"Darstellung","settings_entity":"Entität","settings_display_name":"Anzeigename","settings_display_type":"Darstellungstyp","settings_battery_sensor":"Batteriesensor","settings_show_bars":"Balken anzeigen","settings_show_care_info":"Pflegeinfos anzeigen","settings_hide_species":"Spezies ausblenden","settings_hide_image":"Bild ausblenden","settings_hide_units":"Einheiten ausblenden","settings_show_limits":"Min/Max-Werte anzeigen","settings_full":"Voll","settings_compact":"Kompakt"}'),nl:JSON.parse('{"moisture":"Bodemvochtigheid","conductivity":"Geleidbaarheid","temperature":"Temperatuur","illuminance":"Verlichtingssterkte","humidity":"Luchtvochtigheid","dli":"Dagelijkse lichtintegraal","dli_24h":"DLI (24u voortschrijdend)","co2":"CO2","soil_temperature":"Bodemtemperatuur","vpd":"Dampdrukdeficit","care":"Verzorging","care_watering":"Water geven","care_sunlight":"Zonlicht","care_soil":"Grond","care_pruning":"Snoeien","care_fertilization":"Bemesting","no_care_info":"Geen verzorgingsinformatie beschikbaar.","settings_bars":"Balken","settings_care_info":"Verzorgingsinfo","settings_appearance":"Weergave","settings_entity":"Entiteit","settings_display_name":"Weergavenaam","settings_display_type":"Weergavetype","settings_battery_sensor":"Batterijsensor","settings_show_bars":"Balken tonen","settings_show_care_info":"Verzorgingsinfo tonen","settings_hide_species":"Soortnaam verbergen","settings_hide_image":"Afbeelding verbergen","settings_hide_units":"Eenheden verbergen","settings_show_limits":"Min/Max-waarden tonen","settings_full":"Volledig","settings_compact":"Compact"}')},bt=(t,e="en")=>{var i;return(null===(i=null==t?void 0:t.locale)||void 0===i?void 0:i.language)||(null==t?void 0:t.language)||e},$t=(t,e)=>{var i;const s=bt(t).toLowerCase().replace("_","-").split("-")[0];return(null===(i=yt[s])||void 0===i?void 0:i[e])||yt.en[e]||e},wt="flower-card",xt=["moisture","conductivity","temperature","illuminance","humidity","dli"],At=(t="en")=>[{label:$t({language:t},"moisture"),value:"moisture"},{label:$t({language:t},"conductivity"),value:"conductivity"},{label:$t({language:t},"temperature"),value:"temperature"},{label:$t({language:t},"illuminance"),value:"illuminance"},{label:$t({language:t},"humidity"),value:"humidity"},{label:$t({language:t},"dli"),value:"dli"},{label:$t({language:t},"dli_24h"),value:"dli_24h"},{label:$t({language:t},"co2"),value:"co2"},{label:$t({language:t},"soil_temperature"),value:"soil_temperature"},{label:$t({language:t},"vpd"),value:"vpd"}],Mt=(At("en"),(t="en")=>[{label:$t({language:t},"care_watering"),value:"care_watering"},{label:$t({language:t},"care_sunlight"),value:"care_sunlight"},{label:$t({language:t},"care_soil"),value:"care_soil"},{label:$t({language:t},"care_pruning"),value:"care_pruning"},{label:$t({language:t},"care_fertilization"),value:"care_fertilization"}]),St=Mt("en"),Et={care_watering:"mdi:watering-can-outline",care_sunlight:"mdi:white-balance-sunny",care_soil:"mdi:shovel",care_pruning:"mdi:content-cut",care_fertilization:"mdi:bottle-tonic-outline"};const Dt=(t,e)=>{vt(t,"hass-more-info",{entityId:e},{bubbles:!1,composed:!0})},Ct=t=>{var e;return null!==(e=null==t?void 0:t.startsWith("media-source://"))&&void 0!==e&&e},Nt=t=>{if(!t)return!1;const[e,i]=t.split(".").map(Number);return e>2025||2025===e&&i>=11},Lt=(t,e,i)=>{var s;if("string"==typeof i&&i)return i;const n=t.formatEntityName;return"function"!=typeof n?e.attributes.friendly_name||e.entity_id:"object"==typeof i&&null!==i&&Nt(null===(s=t.config)||void 0===s?void 0:s.version)?n(e,i):n(e)},It=(t,e,i="en")=>t&&e&&0!==e.length?Mt(i).filter(t=>e.includes(t.value)).map(e=>({key:e.value,label:e.label,icon:Et[e.value],text:t[e.value]})).filter(t=>"string"==typeof t.text&&""!==t.text.trim()):[],kt=t=>F`
    ${t.map(t=>F`
        <div class="care-item">
            <div class="care-heading">
                <ha-icon .icon="${t.icon}"></ha-icon>
                <span>${t.label}</span>
            </div>
            <div class="care-text">${t.text}</div>
        </div>
    `)}
`,Ot=t=>{var e;return null!==(e=t.fields)&&void 0!==e?e:St.map(t=>t.value)},jt=t=>{var e;const i=null===(e=t.config)||void 0===e?void 0:e.extra_badges;return i&&0!==i.length?i.map(e=>((t,e)=>{var i;if((t=>"care_info"===t.type)(e))return((t,e)=>{const{icon:i,color:s,tip:n}=((t,e="en")=>{var i,s,n;return{icon:null!==(i=t.icon)&&void 0!==i?i:"mdi:sprout",color:null!==(s=t.color)&&void 0!==s?s:"var(--secondary-text-color)",tip:null!==(n=t.title)&&void 0!==n?n:$t({language:e},"care")}})(e,bt(t._hass));return F`
        <div class="extra-badge tooltip" @click="${i=>{i.stopPropagation(),t.openCareDialog(e)}}">
            <div class="tip" style="text-align:center;">${n}</div>
            <ha-icon .icon="${i}" style="color: ${s}"></ha-icon>
        </div>
    `})(t,e);if(e.text){const t="none"===(null===(i=e.icon)||void 0===i?void 0:i.toLowerCase()),s=e.color||"var(--secondary-text-color)";if(t&&e.show_state)return F`
                <div class="extra-badge tooltip">
                    <div class="tip" style="text-align:center;">${e.text}</div>
                    <span class="badge-text" style="color: ${s}">${e.text}</span>
                </div>
            `;const n=t?"":e.icon||"mdi:information";return F`
            <div class="extra-badge tooltip">
                <div class="tip" style="text-align:center;">${e.text}</div>
                ${t?"":F`<ha-icon .icon="${n}" style="color: ${s}"></ha-icon>`}
                ${e.show_state?F`<span class="badge-text">${e.text}</span>`:""}
            </div>
        `}if(!e.entity&&e.icon){const t=e.color||"var(--secondary-text-color)";return F`
            <div class="extra-badge">
                <ha-icon .icon="${e.icon}" style="color: ${t}"></ha-icon>
            </div>
        `}if(!e.entity)return F``;const s=e.entity,n=t._hass.states[s];if(!n)return F``;const a=s.startsWith("binary_sensor."),o=n.state,r=Lt(t._hass,n);let l,c,d,h=e.icon||n.attributes.icon;if(!h)if(a){const t=n.attributes.device_class,e="on"===o,i={battery:["mdi:battery","mdi:battery-outline"],battery_charging:["mdi:battery-charging","mdi:battery"],cold:["mdi:snowflake","mdi:snowflake-off"],connectivity:["mdi:check-network-outline","mdi:close-network-outline"],door:["mdi:door-open","mdi:door-closed"],garage_door:["mdi:garage-open","mdi:garage"],gas:["mdi:alert-circle","mdi:check-circle"],heat:["mdi:fire","mdi:fire-off"],light:["mdi:brightness-7","mdi:brightness-5"],lock:["mdi:lock-open","mdi:lock"],moisture:["mdi:water","mdi:water-off"],motion:["mdi:motion-sensor","mdi:motion-sensor-off"],moving:["mdi:motion","mdi:motion-off"],occupancy:["mdi:home","mdi:home-outline"],opening:["mdi:square-outline","mdi:square"],plug:["mdi:power-plug","mdi:power-plug-off"],power:["mdi:power","mdi:power-off"],presence:["mdi:home","mdi:home-outline"],problem:["mdi:alert-circle","mdi:check-circle"],running:["mdi:play","mdi:stop"],safety:["mdi:alert-circle","mdi:check-circle"],smoke:["mdi:smoke-detector-alert","mdi:smoke-detector"],sound:["mdi:music-note","mdi:music-note-off"],tamper:["mdi:alert-circle","mdi:check-circle"],update:["mdi:package-up","mdi:package"],vibration:["mdi:vibrate","mdi:vibrate-off"],window:["mdi:window-open","mdi:window-closed"]};h=t&&i[t]?e?i[t][0]:i[t][1]:e?"mdi:checkbox-marked-circle":"mdi:checkbox-blank-circle-outline"}else h="mdi:information";if(l=a&&!e.attribute?"on"===o?e.color_on||"var(--primary-color)":e.color_off||"var(--disabled-text-color)":e.color||"var(--secondary-text-color)",e.attribute){const i=n.attributes[e.attribute];if(d=e.attribute,null==i)c="N/A";else if("last_changed"===e.attribute||"last_updated"===e.attribute){const t="last_changed"===e.attribute?n.last_changed:n.last_updated;c=t?new Date(t).toLocaleString():String(i)}else c=t._hass.formatEntityAttributeValue?t._hass.formatEntityAttributeValue(n,e.attribute):String(i)}else d=r,c=a?o:t._hass.formatEntityState(n);return F`
        <div class="extra-badge tooltip" @click="${e=>{e.stopPropagation(),Dt(t,s)}}">
            <div class="tip" style="text-align:center;">${`${d}: ${c}`}</div>
            <ha-icon .icon="${h}" style="color: ${l}"></ha-icon>
            ${e.show_state?F`<span class="badge-text">${c}</span>`:""}
        </div>
    `})(t,e)):F``},Ut=F`<math style="display: inline-grid;" xmlns="http://www.w3.org/1998/Math/MathML"><mrow><mfrac><mrow><mn>mol</mn></mrow><mrow><mn>d</mn><mn>⋅</mn><msup><mn>m</mn><mn>2</mn></msup></mrow></mfrac></mrow></math>`,Pt=(t,e)=>((t,e,i)=>{const s=e?(t=>{switch(t.number_format){case mt.comma_decimal:return["en-US","en"];case mt.decimal_comma:return["de","es","it"];case mt.space_comma:return["fr","sv","cs"];case mt.system:return;default:return t.language}})(e):void 0;if(Number.isNaN=Number.isNaN||function t(e){return"number"==typeof e&&t(e)},(null==e?void 0:e.number_format)!==mt.none&&!Number.isNaN(Number(t))&&Intl)try{return new Intl.NumberFormat(s,ft(t,i)).format(Number(t))}catch(e){return console.error(e),new Intl.NumberFormat(void 0,ft(t,i)).format(Number(t))}return"string"==typeof t?t:`${((t,e=2)=>Math.round(t*Math.pow(10,e))/Math.pow(10,e))(t,null==i?void 0:i.maximumFractionDigits).toString()}${"currency"===(null==i?void 0:i.style)?` ${i.currency}`:""}`})(t,e,{maximumFractionDigits:10}),Tt=(t,e)=>{var i,s,n;const a=(null===(i=t.config)||void 0===i?void 0:i.display_type)===gt.Compact,o=null!==(n=null===(s=t.config)||void 0===s?void 0:s.bars_per_row)&&void 0!==n?n:a?1:2,r=1===o,l=((t,e)=>Object.values(t).reduce((t,i,s)=>{const n=Math.floor(s/e);return t[n]||(t[n]=[]),t[n].push(i),t},[]))(e,o),c="attributes "+(r?"width-100":"");return l.map(e=>F`<div class="${c}">${e.map(e=>e?F`${((t,e)=>{var i,s,n,a,o,r,l,c,d,h;const{max:p,min:u}=e.limits,g=e.unit_of_measurement,m="lx"===e.unit_of_measurement,_=e.icon||"mdi:help-circle-outline",f=null!==(i=e.current)&&void 0!==i?i:0,v=!isNaN(f)&&null!=f,y=e.display_state,b=!m||f<=0||u<=0?100*Math.max(0,Math.min(1,(f-u)/(p-u))):100*Math.max(0,Math.min(1,(Math.log(f)-Math.log(u))/(Math.log(p)-Math.log(u)))),$=((t,e)=>{var i;return(null===(i=null==t?void 0:t.localize)||void 0===i?void 0:i.call(t,`component.plant.entity.sensor.${e}.name`))||$t(t,e)})(t._hass,e.name),w=v?F`${$}: ${f} ${g}<br>(${u} ~ ${p} ${g})`:t._hass.localize("state.default.unavailable"),x="dli"===e.name||"dli_24h"===e.name?Ut:g,A=(null===(s=t.config)||void 0===s?void 0:s.display_type)===gt.Compact,M=null!==(a=null===(n=t.config)||void 0===n?void 0:n.bars_per_row)&&void 0!==a?a:A?1:2,S=!(null!==(r=null===(o=t.config)||void 0===o?void 0:o.hide_units)&&void 0!==r?r:A),E=null!==(c=null===(l=t.config)||void 0===l?void 0:l.show_limits)&&void 0!==c&&c,D=1===M;return F`
        <div class="${`attribute tooltip ${D?"width-100":""}${D&&S?" has-units":""}${E?" has-limits":""}`}" @click="${()=>Dt(t,e.sensor)}">
            <div class="tip" style="text-align:center;">${w}</div>
            <ha-icon .icon="${_}"></ha-icon>
            <div class="meter red">
                <span class="${v?f<u||f>p?"bad":"good":"unavailable"}" style="width: 100%;"></span>
            </div>
            <div class="meter-wrap">
                <div class="meter green">
                    <span class="${v?f>p?"bad":"good":"unavailable"}" style="width:${v?b:"0"}%;"></span>
                </div>
                ${E?F`<div class="limits"><span class="min">${Pt(u,null===(d=t._hass)||void 0===d?void 0:d.locale)}</span><span class="max">${Pt(p,null===(h=t._hass)||void 0===h?void 0:h.locale)}</span></div>`:""}
            </div>
            <div class="meter red">
                <span class="bad" style="width:${v?f>p?100:0:"0"}%;"></span>
            </div>
            ${S?F`<div class="header"><span class="value">${y}</span>&nbsp;<span class='unit'>${x}</span></div>`:""}
        </div>
    `})(t,e)}`:"")}</div>`).flat()};var zt=function(t,e,i,s){var n,a=arguments.length,o=a<3?e:null===s?s=Object.getOwnPropertyDescriptor(e,i):s;if("object"==typeof Reflect&&"function"==typeof Reflect.decorate)o=Reflect.decorate(t,e,i,s);else for(var r=t.length-1;r>=0;r--)(n=t[r])&&(o=(a<3?n(o):a>3?n(e,i,o):n(e,i))||o);return a>3&&o&&Object.defineProperty(e,i,o),o},Ht=function(t,e,i,s){return new(i||(i=Promise))(function(n,a){function o(t){try{l(s.next(t))}catch(t){a(t)}}function r(t){try{l(s.throw(t))}catch(t){a(t)}}function l(t){var e;t.done?n(t.value):(e=t.value,e instanceof i?e:new i(function(t){t(e)})).then(o,r)}l((s=s.apply(t,e||[])).next())})};console.info("%c FLOWER-CARD %c 2026.11.3","color: cyan; background: black; font-weight: bold;","color: darkblue; background: white; font-weight: bold;");const Rt=()=>{var t,e;if("undefined"==typeof document)return;const i=document.querySelector("home-assistant");return null===(e=null===(t=null==i?void 0:i.hass)||void 0===t?void 0:t.config)||void 0===e?void 0:e.version};window.customCards=window.customCards||[],window.customCards.some(t=>t.type===wt)||window.customCards.push({type:wt,name:"Flower card",preview:!0,description:"Custom flower card for https://github.com/Olen/homeassistant-plant",getEntitySuggestion:(t,e)=>"plant"!==e.split(".")[0]?null:[{label:"Full",config:{type:`custom:${wt}`,entity:e}},{label:"Compact",config:{type:`custom:${wt}`,entity:e,display_type:gt.Compact}}]});class Bt extends rt{constructor(){super(...arguments),this._careDialogOpen=!1,this._careDialogFields=[],this._careDialogTitle="",this._imageDialogOpen=!1,this.previousFetchDate=0,this.plantinfo={result:{}}}set hass(t){var e,i;this._hass=t,this.stateObj=(null===(e=this.config)||void 0===e?void 0:e.entity)?t.states[this.config.entity]:void 0;const s=null===(i=this.stateObj)||void 0===i?void 0:i.attributes.entity_picture;s!==this._lastEntityPicture&&(this._lastEntityPicture=s,this._resolveEntityPicture(t,s)),Date.now()>this.previousFetchDate+1e3&&(this.previousFetchDate=Date.now(),this.get_data(t).then(()=>{this.requestUpdate()}))}_resolveEntityPicture(t,e){return Ht(this,void 0,void 0,function*(){e?Ct(e)?(this._resolvedImageUrl=yield((t,e)=>function(t,e,i,s){return new(i||(i=Promise))(function(n,a){function o(t){try{l(s.next(t))}catch(t){a(t)}}function r(t){try{l(s.throw(t))}catch(t){a(t)}}function l(t){var e;t.done?n(t.value):(e=t.value,e instanceof i?e:new i(function(t){t(e)})).then(o,r)}l((s=s.apply(t,e||[])).next())})}(void 0,void 0,void 0,function*(){if(!Ct(e))return e;try{return(yield t.callWS({type:"media_source/resolve_media",media_content_id:e})).url}catch(t){return console.error("Failed to resolve media source:",t),""}}))(t,e),this.requestUpdate()):this._resolvedImageUrl=e:this._resolvedImageUrl=void 0})}static getConfigForm(){const t="undefined"==typeof document?"en":(null===(e=document.documentElement)||void 0===e?void 0:e.lang)||"en";var e,i;return{schema:[{name:"entity",required:!0,selector:{entity:{domain:"plant"}}},(i=Rt(),Nt(i)?{name:"name",selector:{entity_name:{}},context:{entity:"entity"}}:{name:"name",selector:{text:{}}}),{name:"battery_sensor",selector:{entity:{domain:"sensor",device_class:"battery"}}},{type:"expandable",name:"",title:$t({language:t},"settings_bars"),schema:[{name:"show_bars",selector:{select:{multiple:!0,options:At(t)}}}]},{type:"expandable",name:"",title:$t({language:t},"settings_care_info"),schema:[{name:"show_care",selector:{select:{multiple:!0,options:Mt(t)}}}]},{type:"expandable",name:"",title:$t({language:t},"settings_appearance"),schema:[{name:"display_type",selector:{select:{options:[{value:"full",label:$t({language:t},"settings_full")},{value:"compact",label:$t({language:t},"settings_compact")}]}}},{name:"hide_species",selector:{boolean:{}}},{name:"hide_image",selector:{boolean:{}}},{name:"hide_units",selector:{boolean:{}}},{name:"show_limits",selector:{boolean:{}}}]}],computeLabel:e=>({entity:$t({language:t},"settings_entity"),name:$t({language:t},"settings_display_name"),display_type:$t({language:t},"settings_display_type"),battery_sensor:$t({language:t},"settings_battery_sensor"),show_bars:$t({language:t},"settings_show_bars"),show_care:$t({language:t},"settings_show_care_info"),hide_species:$t({language:t},"settings_hide_species"),hide_image:$t({language:t},"settings_hide_image"),hide_units:$t({language:t},"settings_hide_units"),show_limits:$t({language:t},"settings_show_limits")}[e.name]||e.name)}}static getStubConfig(t){const e=t=>"object"==typeof t&&null!==t&&"entity_id"in t&&"string"==typeof t.entity_id&&t.entity_id.startsWith("plant.");let i=[];try{i=Object.values(t.states).filter(e)}catch(t){console.info(`Unable to get ha-data: ${t}`)}return{entity:i.length>0?i[0].entity_id:"plant.my_plant",battery_sensor:"sensor.myflower_battery",show_bars:xt}}setConfig(t){if(!t.entity)throw new Error("You need to define an entity");this.config=t}openCareDialog(t){const{open:e,fields:i,title:s}=((t,e="en")=>{var i;return{open:!0,fields:Ot(t),title:null!==(i=t.title)&&void 0!==i?i:$t({language:e},"care")}})(t,bt(this._hass));this._careDialogFields=i,this._careDialogTitle=s,this._careDialogOpen=e}_closeCareDialog(){this._careDialogOpen=!1}renderCareDialog(){var t,e,i;const s=null===(t=this.config)||void 0===t?void 0:t.entity,n=s?null===(i=null===(e=this._hass)||void 0===e?void 0:e.states[s])||void 0===i?void 0:i.attributes:void 0,a=bt(this._hass),o=It(n,this._careDialogFields,a);return F`
            <ha-dialog
                open
                header-title="${this._careDialogTitle}"
                heading="${this._careDialogTitle}"
                @closed="${()=>this._closeCareDialog()}"
            >
                ${o.length>0?F`<div class="care-info care-info--dialog">${kt(o)}</div>`:F`<div class="care-info-empty">${$t({language:a},"no_care_info")}</div>`}
            </ha-dialog>
        `}openImageDialog(){this._imageDialogOpen=!0}_closeImageDialog(){this._imageDialogOpen=!1}renderImageDialog(){var t;const e=this.stateObj?Lt(this._hass,this.stateObj,null===(t=this.config)||void 0===t?void 0:t.name):"";return F`
            <ha-dialog open @closed="${()=>this._closeImageDialog()}">
                <div class="image-dialog">
                    <img src="${this._resolvedImageUrl}" alt="${e}">
                    ${e?F`<div class="image-dialog-caption">${e}</div>`:""}
                </div>
            </ha-dialog>
        `}render(){var t,e;if(!this.config||!this._hass)return F``;if(!this.stateObj)return this._careDialogOpen=!1,this._imageDialogOpen=!1,F`
                <hui-warning>
                Entity not available: ${this.config.entity}
                </hui-warning>
              `;const i=this.stateObj,s=i.attributes.species,n=Lt(this._hass,i,this.config.name),a=null!==(t=this.config.hide_species)&&void 0!==t&&t,o=null!==(e=this.config.hide_image)&&void 0!==e&&e,r=((t,e)=>!t&&!!e)(o,this._resolvedImageUrl),l=this.config.display_type===gt.Compact?"header-compact":"header",c=this.config.display_type===gt.Compact||o?"":"card-margin-top";return F`
            <ha-card class="${c}">
            <div class="${l}${o?" no-image":""}" @click="${()=>Dt(this,i.entity_id)}">
                ${o?"":F`<img
                    src="${this._resolvedImageUrl||"data:image/svg+xml;base64,PHN2ZyB4bWxucz0naHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmcnIHByZXNlcnZlQXNwZWN0UmF0aW89InhNaWRZTWlkIG1lZXQiIGZvY3VzYWJsZT0iZmFsc2UiIHJvbGU9ImltZyIgYXJpYS1oaWRkZW49InRydWUiIHZpZXdCb3g9IjAgMCAyNCAyNCI+CiAgICAgIDxnPgogICAgICA8IS0tP2xpdCQ0MTM0MjMxNjkkLS0+PHBhdGggZD0iTTMsMTNBOSw5IDAgMCwwIDEyLDIyQzEyLDE3IDcuOTcsMTMgMywxM00xMiw1LjVBMi41LDIuNSAwIDAsMSAxNC41LDhBMi41LDIuNSAwIDAsMSAxMiwxMC41QTIuNSwyLjUgMCAwLDEgOS41LDhBMi41LDIuNSAwIDAsMSAxMiw1LjVNNS42LDEwLjI1QTIuNSwyLjUgMCAwLDAgOC4xLDEyLjc1QzguNjMsMTIuNzUgOS4xMiwxMi41OCA5LjUsMTIuMzFDOS41LDEyLjM3IDkuNSwxMi40MyA5LjUsMTIuNUEyLjUsMi41IDAgMCwwIDEyLDE1QTIuNSwyLjUgMCAwLDAgMTQuNSwxMi41QzE0LjUsMTIuNDMgMTQuNSwxMi4zNyAxNC41LDEyLjMxQzE0Ljg4LDEyLjU4IDE1LjM3LDEyLjc1IDE1LjksMTIuNzVDMTcuMjgsMTIuNzUgMTguNCwxMS42MyAxOC40LDEwLjI1QzE4LjQsOS4yNSAxNy44MSw4LjQgMTYuOTcsOEMxNy44MSw3LjYgMTguNCw2Ljc0IDE4LjQsNS43NUMxOC40LDQuMzcgMTcuMjgsMy4yNSAxNS45LDMuMjVDMTUuMzcsMy4yNSAxNC44OCwzLjQxIDE0LjUsMy42OUMxNC41LDMuNjMgMTQuNSwzLjU2IDE0LjUsMy41QTIuNSwyLjUgMCAwLDAgMTIsMUEyLjUsMi41IDAgMCwwIDkuNSwzLjVDOS41LDMuNTYgOS41LDMuNjMgOS41LDMuNjlDOS4xMiwzLjQxIDguNjMsMy4yNSA4LjEsMy4yNUEyLjUsMi41IDAgMCwwIDUuNiw1Ljc1QzUuNiw2Ljc0IDYuMTksNy42IDcuMDMsOEM2LjE5LDguNCA1LjYsOS4yNSA1LjYsMTAuMjVNMTIsMjJBOSw5IDAgMCwwIDIxLDEzQzE2LDEzIDEyLDE3IDEyLDIyWiI+PC9wYXRoPgogICAgICA8L2c+Cjwvc3ZnPgo="}"
                    class="${r?"has-lightbox":""}"
                    @click="${t=>{r&&(t.stopPropagation(),this.openImageDialog())}}">`}
                <span id="name"> ${n} <ha-icon .icon="mdi:${"problem"==i.state.toLowerCase()?"alert-circle-outline":""}"></ha-icon>
                </span>
                <span id="battery">${jt(this)}${(t=>{var e,i;const s=t.config;if(!(null==s?void 0:s.battery_sensor))return F``;const n=s.battery_sensor,a=t._hass.states[n];if(!a)return F``;const o=parseInt(a.state),r=null!==(e=s.battery_warn_level)&&void 0!==e?e:20,l=null!==(i=s.battery_ok_level)&&void 0!==i?i:40,c=([{threshold:90,icon:"mdi:battery"},{threshold:80,icon:"mdi:battery-90"},{threshold:70,icon:"mdi:battery-80"},{threshold:60,icon:"mdi:battery-70"},{threshold:50,icon:"mdi:battery-60"},{threshold:40,icon:"mdi:battery-50"},{threshold:30,icon:"mdi:battery-40"},{threshold:20,icon:"mdi:battery-30"},{threshold:10,icon:"mdi:battery-20"},{threshold:0,icon:"mdi:battery-10"},{threshold:-1/0,icon:"mdi:battery-alert-variant-outline"}].find(({threshold:t})=>o>t)||{threshold:-1/0,icon:"mdi:battery-alert-variant-outline"}).icon,d=(h=o)>=l?"green":h>=r?"orange":"red";var h;return F`
        <div class="battery tooltip" @click="${e=>{e.stopPropagation(),Dt(t,n)}}">
            <div class="tip" style="text-align:center;">${o}%</div>
            <ha-icon .icon="${c}" style="color: ${d}"></ha-icon>
        </div>
    `})(this)}</span>
                ${a?"":F`<span id="species">${s}</span>`}
            </div>
            <div class="divider"></div>
            ${(t=>{var e,i;const s={},n=(null===(e=t.config)||void 0===e?void 0:e.show_bars)||xt;if(t.plantinfo&&t.plantinfo.result){const e=t.plantinfo.result;for(const a of n)if(e[a])try{const{max:n,min:o,current:r,icon:l,sensor:c}=e[a],d=t._hass.states[c];if(!d)continue;const h=t._hass.formatEntityState(d).replace(/[^\d,.+-]/g,""),p=(null===(i=null==d?void 0:d.attributes)||void 0===i?void 0:i.unit_of_measurement)||e[a].unit_of_measurement||"",u={max:Number(n),min:Number(o)};s[a]={name:a,current:Number(r),limits:u,icon:String(l),sensor:String(c),unit_of_measurement:String(p),display_state:h}}catch(t){console.warn(`Flower card: Error processing ${a}:`,t)}}return Tt(t,s)})(this)}
            ${(t=>{var e;const i=t.config;if(!i)return F``;const s=i.entity,n=s?null===(e=t._hass.states[s])||void 0===e?void 0:e.attributes:void 0,a=It(n,i.show_care,bt(t._hass));return 0===a.length?F``:F`
        <div class="care-info">
            ${kt(a)}
        </div>
    `})(this)}
            </ha-card>
            ${this._careDialogOpen?this.renderCareDialog():F``}
            ${this._imageDialogOpen?this.renderImageDialog():F``}
            `}get_data(t){return Ht(this,void 0,void 0,function*(){var e,i;try{this.plantinfo=yield t.callWS({type:"plant/get_info",entity_id:null===(e=this.config)||void 0===e?void 0:e.entity})}catch(t){console.warn(`Flower card: Failed to fetch data for ${null===(i=this.config)||void 0===i?void 0:i.entity}:`,t),this.plantinfo&&this.plantinfo.result&&0!==Object.keys(this.plantinfo.result).length||(this.plantinfo={result:{}})}})}getCardSize(){return 5}static get styles(){return ut}}zt([ht()],Bt.prototype,"_hass",void 0),zt([ht()],Bt.prototype,"config",void 0),zt([pt()],Bt.prototype,"_careDialogOpen",void 0),zt([pt()],Bt.prototype,"_careDialogFields",void 0),zt([pt()],Bt.prototype,"_careDialogTitle",void 0),zt([pt()],Bt.prototype,"_imageDialogOpen",void 0),customElements.get(wt)||customElements.define(wt,Bt)})();
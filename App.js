import React, { useState } from 'react';
import { StyleSheet, Text, View, TextInput, TouchableOpacity, FlatList, ScrollView, SafeAreaView } from 'react-native';

// --- BANCO DE DADOS LOCAL DE CIFTAS (Focado em Refrões) ---
const BANCO_DE_CIFRAS = [
  {
    id: '1',
    titulo: 'Cobaia',
    artista: 'Lauana Prado',
    tomOriginal: 'D',
    trecho: 'Refrão',
    cifra: "D               A\n  Eu sou a sua cobaia\nBm               G\n  E você testando amor...\nD                  A\n  Tentando achar alguém pra dar certo\nBm                     G\n  Enquanto eu tô aqui sofrendo de perto!"
  },
  {
    id: '2',
    titulo: 'Me Leva Pra Casa',
    artista: 'Lauana Prado',
    tomOriginal: 'G',
    trecho: 'Refrão',
    cifra: "G               D\n  Me leva pra casa, meu amor\nC                     G\n  Não deixe o nosso fogo apagar\nC                  G\n  A noite tá fria, o peito vazio\n    A7             D7\n  Vem me abraçar..."
  },
  {
    id: '3',
    titulo: 'Vingança',
    artista: 'Lauana Prado',
    tomOriginal: 'A',
    trecho: 'Refrão',
    cifra: "A                 E\n  E agora, quem vai apagar o incêndio\nF#m                D\n  Que você deixou aqui dentro?\nA                    E\n  Cê acha que amor é brincadeira\n      D                    E\n  E jogou nossa história na lixeira!"
  }
];

const ESCALA = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];

// Transpõe os acordes de uma cifra do tom original para o tom atual
function transporCifra(cifraOriginal, tomOriginal, tomAtual) {
  const indexOriginal = ESCALA.indexOf(tomOriginal);
  const indexAtual = ESCALA.indexOf(tomAtual);
  const passos = indexAtual - indexOriginal;

  if (passos === 0) return cifraOriginal;

  return cifraOriginal.replace(/\b[A-G][#b]?[m7maj4sus]*\b/g, (acorde) => {
    const match = acorde.match(/^[A-G][#b]*/);
    if (!match) return acorde;
    const notaBase = match[0];
    const idxNota = ESCALA.indexOf(notaBase);
    if (idxNota === -1) return acorde;

    let novoIdx = (idxNota + passos) % 12;
    if (novoIdx < 0) novoIdx += 12;
    return acorde.replace(notaBase, ESCALA[novoIdx]);
  });
}

export default function App() {
  const [telaAtual, setTelaAtual] = useState('home'); // 'home', 'pasta', 'busca', 'cifra'
  const [pastas, setPastas] = useState([
    { id: '1', nome: 'Churrasco com Amigos', musicas: [BANCO_DE_CIFRAS[0], BANCO_DE_CIFRAS[1]] },
    { id: '2', nome: 'Lauana Prado - Só Hits', musicas: [BANCO_DE_CIFRAS[0], BANCO_DE_CIFRAS[2]] }
  ]);
  const [pastaSelecionada, setPastaSelecionada] = useState(null);
  const [musicaSelecionada, setMusicaSelecionada] = useState(null);
  const [termoBusca, setTermoBusca] = useState('');
  const [tomAtual, setTomAtual] = useState('D');

  // --- TELA 1: HOME (Lista de Pastas) ---
  if (telaAtual === 'home') {
    return (
      <SafeAreaView style={styles.container}>
        <Text style={styles.headerTitle}>🎸 RefrãoCifras</Text>
        <Text style={styles.subtitle}>Suas pastas de rodas de violão</Text>

        <FlatList
          data={pastas}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => (
            <TouchableOpacity
              style={styles.card}
              onPress={() => { setPastaSelecionada(item); setTelaAtual('pasta'); }}
            >
              <Text style={styles.cardTitle}>{item.nome}</Text>
              <Text style={styles.cardSub}>{item.musicas.length} músicas cadastradas</Text>
            </TouchableOpacity>
          )}
        />
      </SafeAreaView>
    );
  }

  // --- TELA 2: DETALHES DA PASTA (Músicas na Pasta) ---
  if (telaAtual === 'pasta') {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.navBar}>
          <TouchableOpacity onPress={() => setTelaAtual('home')}><Text style={styles.backButton}>← Voltar</Text></TouchableOpacity>
          <Text style={styles.headerTitleSmall}>{pastaSelecionada.nome}</Text>
          <View style={{width: 50}} />
        </View>

        <TouchableOpacity
          style={styles.primaryButton}
          onPress={() => setTelaAtual('busca')}
        >
          <Text style={styles.primaryButtonText}>+ Adicionar Música da Busca</Text>
        </TouchableOpacity>

        <FlatList
          data={pastaSelecionada.musicas}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => (
            <TouchableOpacity
              style={styles.card}
              onPress={() => {
                setMusicaSelecionada(item);
                setTomAtual(item.tomOriginal);
                setTelaAtual('cifra');
              }}
            >
              <Text style={styles.cardTitle}>{item.titulo}</Text>
              <Text style={styles.cardSub}>{item.artista} • Tom: {item.tomOriginal}</Text>
            </TouchableOpacity>
          )}
        />
      </SafeAreaView>
    );
  }

  // --- TELA 3: BUSCA LOCAL PARA ADICIONAR ---
  if (telaAtual === 'busca') {
    const musicasFiltradas = BANCO_DE_CIFRAS.filter(m =>
      m.titulo.toLowerCase().includes(termoBusca.toLowerCase()) ||
      m.artista.toLowerCase().includes(termoBusca.toLowerCase())
    );

    const adicionarMusicaNaPasta = (musica) => {
      if (!pastaSelecionada.musicas.some(m => m.id === musica.id)) {
        pastaSelecionada.musicas.push(musica);
      }
      setTelaAtual('pasta');
    };

    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.navBar}>
          <TouchableOpacity onPress={() => setTelaAtual('pasta')}><Text style={styles.backButton}>← Voltar</Text></TouchableOpacity>
          <Text style={styles.headerTitleSmall}>Buscar Cifra</Text>
          <View style={{width: 50}} />
        </View>

        <TextInput
          style={styles.searchInput}
          placeholder="Digite o nome da música ou artista..."
          placeholderTextColor="#666"
          value={termoBusca}
          onChangeText={setTermoBusca}
          autoFocus={true}
        />

        <FlatList
          data={musicasFiltradas}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => (
            <TouchableOpacity
              style={styles.card}
              onPress={() => adicionarMusicaNaPasta(item)}
            >
              <Text style={styles.cardTitle}>{item.titulo} <Text style={{color: '#4CD964', fontSize: 14}}>[+ Adicionar]</Text></Text>
              <Text style={styles.cardSub}>{item.artista} • Tom: {item.tomOriginal}</Text>
            </TouchableOpacity>
          )}
        />
      </SafeAreaView>
    );
  }

  // --- TELA 4: EXIBIÇÃO DA CIFRA (Com Transposição) ---
  if (telaAtual === 'cifra') {
    const alterarTom = (direcao) => {
      const idx = ESCALA.indexOf(tomAtual);
      let novoIdx = idx + direcao;
      if (novoIdx > 11) novoIdx = 0;
      if (novoIdx < 0) novoIdx = 11;
      setTomAtual(ESCALA[novoIdx]);
    };

    const cifraTransposta = transporCifra(musicaSelecionada.cifra, musicaSelecionada.tomOriginal, tomAtual);

    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.navBar}>
          <TouchableOpacity onPress={() => setTelaAtual('pasta')}><Text style={styles.backButton}>← Voltar</Text></TouchableOpacity>
          <View style={styles.toneControl}>
            <TouchableOpacity onPress={() => alterarTom(-1)} style={styles.toneBtn}><Text style={styles.toneBtnText}>-</Text></TouchableOpacity>
            <Text style={styles.toneText}>Tom: {tomAtual}</Text>
            <TouchableOpacity onPress={() => alterarTom(1)} style={styles.toneBtn}><Text style={styles.toneBtnText}>+</Text></TouchableOpacity>
          </View>
        </View>

        <View style={styles.cifraHeader}>
          <Text style={styles.cifraTitle}>{musicaSelecionada.titulo}</Text>
          <Text style={styles.cifraArtist}>{musicaSelecionada.artista} ({musicaSelecionada.trecho})</Text>
        </View>

        <ScrollView style={styles.cifraContainer}>
          <Text style={styles.cifraText}>{cifraTransposta}</Text>
        </ScrollView>
      </SafeAreaView>
    );
  }
}

// --- ESTILOS DO APLICATIVO ---
const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#121212', padding: 20 },
  headerTitle: { fontSize: 26, fontWeight: 'bold', color: '#FFF', marginTop: 10 },
  headerTitleSmall: { fontSize: 18, fontWeight: 'bold', color: '#FFF' },
  subtitle: { fontSize: 14, color: '#888', marginBottom: 20 },
  card: { backgroundColor: '#1E1E1E', padding: 16, borderRadius: 10, marginBottom: 12 },
  cardTitle: { fontSize: 18, fontWeight: 'bold', color: '#FFF' },
  cardSub: { fontSize: 14, color: '#AAA', marginTop: 4 },
  navBar: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20, marginTop: 10 },
  backButton: { color: '#FF9500', fontSize: 16, fontWeight: 'bold' },
  primaryButton: { backgroundColor: '#FF9500', padding: 14, borderRadius: 10, alignItems: 'center', marginBottom: 20 },
  primaryButtonText: { color: '#000', fontSize: 16, fontWeight: 'bold' },
  searchInput: { backgroundColor: '#1E1E1E', color: '#FFF', padding: 14, borderRadius: 10, fontSize: 16, marginBottom: 15 },
  toneControl: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#1E1E1E', borderRadius: 8, padding: 4 },
  toneBtn: { paddingHorizontal: 12, paddingVertical: 4 },
  toneBtnText: { color: '#FF9500', fontSize: 18, fontWeight: 'bold' },
  toneText: { color: '#FFF', fontSize: 16, fontWeight: 'bold', marginHorizontal: 8 },
  cifraHeader: { marginBottom: 15 },
  cifraTitle: { fontSize: 22, fontWeight: 'bold', color: '#FFF' },
  cifraArtist: { fontSize: 14, color: '#FF9500', marginTop: 2 },
  cifraContainer: { backgroundColor: '#181818', padding: 16, borderRadius: 10, flex: 1 },
  cifraText: { fontFamily: 'monospace', color: '#E0E0E0', fontSize: 16, lineHeight: 24 }
});
